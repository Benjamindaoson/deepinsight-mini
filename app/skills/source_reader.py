"""Bounded public-source reader. Content is evidence, never executable instructions."""
import hashlib
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import feedparser
import httpx
import trafilatura
import yaml
from lxml import html as lxml_html

from app.config import ROOT, config

AGENT = "LondonOfficeIntelligence/0.1"
MAX_BYTES = 10 * 1024 * 1024


def registry():
    return yaml.safe_load((ROOT / "config/sources.yaml").read_text(encoding="utf-8"))["sources"]


def canonical_url(url):
    p = urlsplit(url)
    query = urlencode(sorted((k, v) for k, v in parse_qsl(p.query)
                             if not k.lower().startswith("utm_") and k not in {"fbclid", "gclid"}))
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or "/", query, ""))


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def digest(content):
    return hashlib.sha256(content if isinstance(content, bytes) else content.encode()).hexdigest()


def validate_url(url, hosts):
    p = urlsplit(url)
    if p.scheme != "https" or p.hostname not in hosts or p.username or p.password or p.port not in (None, 443):
        raise ValueError("Only registered HTTPS source hosts are allowed.")
    for addr in socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM):
        address = ipaddress.ip_address(addr[4][0])
        tunnel = os.getenv("MINI_TUNNEL_DNS") == "1" and any(address in net for net in (
            ipaddress.ip_network("198.18.0.0/15"), ipaddress.ip_network("2001:2::/48")) if address.version == net.version)
        if not address.is_global and not tunnel:
            raise ValueError("Private and special network addresses are not allowed.")


def download(url, hosts, timeout=25):
    with httpx.Client(timeout=httpx.Timeout(timeout), follow_redirects=False,
                      headers={"User-Agent": AGENT, "Accept": "text/html,application/pdf,application/rss+xml"}) as client:
        deadline = time.monotonic() + timeout
        for _ in range(4):
            validate_url(url, hosts)
            with client.stream("GET", url) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers["location"])
                    continue
                response.raise_for_status()
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_BYTES or time.monotonic() > deadline:
                        raise ValueError("Source exceeded download size or duration limit.")
                return bytes(data), str(response.url), response.headers.get("content-type", "")
        raise ValueError("Too many redirects.")


def check_robots(url, hosts, timeout):
    p = urlsplit(url)
    robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
    try:
        body, _, _ = download(robots_url, hosts, timeout)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return "robots.txt absent (404); public access only"
        raise ValueError(f"Robots policy unavailable: HTTP {exc.response.status_code}") from None
    parser = RobotFileParser()
    parser.parse(body.decode("utf-8", errors="replace").splitlines())
    if not parser.can_fetch(AGENT, url):
        raise ValueError("Robots policy disallows this collection path.")
    return "robots.txt permits agent path; no paywall bypass; local evidence audit only"


def pdf_pages(path):
    script = ("import pymupdf as fitz,json,sys; d=fitz.open(sys.argv[1]); "
              "assert len(d)<=150,'PDF page limit'; "
              "print(json.dumps([{'page':i+1,'text':p.get_text()} for i,p in enumerate(d)]))")
    result = subprocess.run([sys.executable, "-c", script, str(path)], capture_output=True,
                            timeout=20, check=True, encoding="utf-8")
    return json.loads(result.stdout)


def parse_date(value):
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        return dt.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
        except ValueError:
            return None


def read_source(source, data_dir=None):
    hosts = {urlsplit(s["url"]).hostname for s in registry()}
    hosts |= set(source.get("allowed_redirect_hosts", []))
    timeout = min(int(source.get("timeout", 25)), 40)
    access = check_robots(source["url"], hosts, timeout)
    last_error = None
    for _ in range(min(int(source.get("retries", 1)), 2) + 1):
        try:
            raw, url, content_type = download(source["url"], hosts, timeout)
            break
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
    else:
        raise last_error
    raw_hash = digest(raw)
    folder = (data_dir or config().data) / "documents"
    folder.mkdir(parents=True, exist_ok=True)
    is_pdf = "pdf" in content_type or raw.startswith(b"%PDF")
    path = folder / (raw_hash + (".pdf" if is_pdf else ".bin"))
    if not path.exists():
        path.write_bytes(raw)
    base = dict(source_id=source["id"], publisher=source["name"], raw_hash=raw_hash,
                raw_path=str(path), geography=", ".join(source.get("geographies", [])),
                access=access, pages=[])
    if source["collection_method"] == "json":
        obj = json.loads(raw)
        if not isinstance(obj,dict) or not isinstance(obj.get("description"),dict):
            raise ValueError("Official series JSON does not match the expected description/time-series contract.")
        text = json.dumps(obj,ensure_ascii=False,sort_keys=True)
        description = obj["description"]
        return [base | dict(url=canonical_url(url),title=description.get("title",source["name"]),text=text,
            hash=digest(text),published_at=parse_date(description.get("releaseDate")),pages=[])]
    if source["collection_method"] == "rss":
        feed = feedparser.parse(raw)
        if not feed.entries:
            raise ValueError("No RSS/Atom entries could be extracted.")
        docs = []
        for entry in feed.entries[:30]:
            link = entry.get("link", "")
            if urlsplit(link).hostname not in hosts:
                continue
            summary = re.sub(r"<[^>]*>", " ", entry.get("summary", ""))
            text = normalize(entry.get("title", "") + "\n" + summary)
            if not re.search(r"office (?:scheme|space|building|development|market)|planning (?:approv|application)|City Plan 2040|pre-let|office-led", entry.get("title", ""), re.I):
                continue
            docs.append(base | dict(url=canonical_url(link), title=entry.get("title", source["name"]),
                text=text, hash=digest(text), published_at=parse_date(entry.get("published")),
                metadata_only=True))
        return docs
    if is_pdf:
        pages = pdf_pages(path)
        text = "\n".join(p["text"] for p in pages)
        title = source["name"]
        published = source.get("publication_date")
    else:
        html = raw.decode("utf-8", errors="replace")
        extracted = trafilatura.bare_extraction(html, url=url, include_comments=False,
                       include_tables=True, favor_precision=True, with_metadata=True)
        if not extracted:
            raise ValueError("Main article could not be reliably extracted.")
        obj = extracted.as_dict() if hasattr(extracted, "as_dict") else extracted
        text = obj.get("text", "")
        title = obj.get("title") or source["name"]
        published = publication_date(html, source.get("publication_date"))
        pages = []
    if len(normalize(text)) < 150:
        raise ValueError("Insufficient primary text for reliable evidence.")
    return [base | dict(url=canonical_url(url), title=title, text=text,
                       hash=digest(normalize(text)), published_at=parse_date(published), pages=pages)]


def publication_date(html, fallback=None):
    """Prefer explicit article metadata/header, never a related story's most recent date."""
    root = lxml_html.fromstring(html)
    # A union XPath returns document order, allowing unrelated global metadata to win.
    for selector in ('//time[contains(@class,"content-header")]/@datetime',
                     '//article//time/@datetime', '//meta[@property="article:published_time"]/@content'):
        for value in root.xpath(selector):
            if parse_date(value):
                return value
    match = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
    return match.group(1) if match and parse_date(match.group(1)) else fallback
