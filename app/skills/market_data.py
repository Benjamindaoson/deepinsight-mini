"""Conservative source-specific extraction. No autonomous quantitative approval."""
import re
import json
import math
from datetime import datetime

from app.database import uid


def extract_observations(document, source):
    if source.get("collection_method") == "json":
        return extract_official_series(document, source)
    if source.get("id") == "boe_bank_rate":
        matches = list(re.finditer(r"(\d{2} [A-Za-z]{3} \d{2})\s*\|?\s*(\d+\.\d+)",document["text"]))
        results=[]
        for match in matches[:12]:
            date,value=match.groups()
            results.append(dict(id=uid(),metric="bank_rate",geography="UK",period=datetime.strptime(date,"%d %b %y").strftime("%Y-%m-%d"),
                value=float(value),unit="percent",definition="Official Bank Rate effective from date",publisher=document["publisher"],
                evidence_text=match.group(0),page=None,review_status="PENDING_REVIEW"))
        return results
    if source.get("id") != "savills_q2_2026":
        return []
    text = document["text"]
    rules = [
        ("prime_rent", "City", "2026Q2", "GBP/sq ft/year", "Savills City prime achieved rent",
         r"the City prime rent stood at £([\d,.]+) per sq ft"),
        ("prime_rent", "West End", "2026H1", "GBP/sq ft/year", "Savills West End average prime achieved rent",
         r"The West End average prime rent at £([\d,.]+) per sq ft"),
        ("grade_a_rent", "City", "2026H1", "GBP/sq ft/year", "Savills City average Grade A achieved rent",
         r"the City average Grade A rent reaching £([\d,.]+) per sq ft"),
        ("grade_a_rent", "West End", "2026H1", "GBP/sq ft/year", "Savills West End average Grade A achieved rent",
         r"In the West End, the average Grade A rent stood at £([\d,.]+) per sq ft"),
        ("vacancy_rate", "City", "2026Q2", "percent", "Savills overall City vacancy",
         r"The City vacancy rate remained unchanged at ([\d.]+)%"),
        ("vacancy_rate", "Central London", "2026Q2", "percent", "Savills overall Central London vacancy",
         r"vacancy rate declined by 20 bps to ([\d.]+)%"),
        ("vacancy_rate", "City Fringe", "2026Q2", "percent", "Savills City Fringe vacancy",
         r"City Fringe vacancy rate, which stood at ([\d.]+)%"),
        ("availability", "Central London", "2026Q2", "million sq ft", "Savills available supply across Central London",
         r"Supply across Central London fell to ([\d.]+) million sq ft"),
        ("take_up", "Central London", "2026Q2", "million sq ft", "Savills quarterly leasing take-up",
         r"take-up reaching ([\d.]+) million sq ft"),
        ("take_up", "Central London", "2026H1", "million sq ft", "Savills half-year leasing take-up",
         r"H1 take-up totalled ([\d.]+) million sq ft"),
        ("leasing_transactions", "Central London", "2026Q2", "transactions", "Savills quarterly leasing transactions",
         r"million sq ft across ([\d,]+) transactions"),
        ("development_completions", "Central London", "2026Q2", "million sq ft", "Savills completed developments and major refurbishments",
         r"Development completions reached ([\d.]+) million sq ft in Q2 2026"),
        ("construction_pipeline", "Central London", "2026H1", "million sq ft", "Savills space under construction at end H1",
         r"space under construction stood at ([\d.]+) million sq ft"),
        ("prelet_share", "Central London", "2026H2", "percent", "Savills scheduled 2026 delivery space already pre-let",
         r"However, ([\d.]+)% of this space has already been pre-let"),
        ("grade_a_take_up_share", "Central London", "2026H1", "percent", "Savills Grade A share of H1 leasing take-up",
         r"Grade A office space, which accounted for ([\d.]+)% of H1 take-up"),
        ("breeam_take_up_share", "Central London", "2026H1", "percent", "Savills BREEAM Excellent and Outstanding share of acquired space",
         r"BREEAM Excellent and Outstanding-rated space accounted for ([\d.]+)%"),
        ("active_demand", "Central London", "2026H1", "million sq ft", "Savills active Central London occupier demand at end H1",
         r"active Central London demand rose to a new record level of ([\d.]+) million sq ft"),
    ]
    results = []
    for metric, geography, period, unit, definition, pattern in rules:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        # A candidate unit/period interpretation is retained for human review.
        quote = text[max(0, match.start() - 30):min(len(text), match.end() + 180)]
        page = next((p["page"] for p in document.get("pages", []) if match.group(0) in p["text"]), None)
        results.append(dict(id=uid(), metric=metric, geography=geography, period=period,
            value=float(match.group(1).replace(",", "")), unit=unit, definition=definition,
            publisher=document["publisher"], evidence_text=quote, page=page,
            review_status="PENDING_REVIEW"))
    return results


def extract_official_series(document, source):
    obj=json.loads(document["text"])
    description=obj.get("description",{})
    rows=[]
    months={m.upper():i for i,m in enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],1)}
    series=obj.get("months",[]) if source.get("frequency")=="monthly" else obj.get("quarters",[])
    for item in series[-24:]:
        date=item.get("date","")
        try:
            value=float(item["value"])
            if not math.isfinite(value):
                continue
            year,part=date.split()
            period=year+(f'M{months[part.upper()]:02}' if source.get("frequency")=="monthly" else part)
        except (ValueError,KeyError):
            continue
        rows.append(dict(id=uid(),metric=source["metric"],geography="UK",period=period,value=value,
            unit="percent",definition=description.get("title",source["name"]),publisher=document["publisher"],
            evidence_text=json.dumps(item,ensure_ascii=False,sort_keys=True),page=None,review_status="PENDING_REVIEW"))
    return rows


def market_data(store, geography="", metric=""):
    rows = store.query("""SELECT o.*,d.url,d.title,d.status document_status,s.status source_health
        FROM observations o JOIN documents d ON d.id=o.document_id JOIN sources s ON s.id=d.source_id
        WHERE (?='' OR o.geography=?) AND (?='' OR o.metric=?) ORDER BY o.period DESC LIMIT 50""",
        (geography, geography, metric, metric))
    return {"observations": rows, "publication_rule": "Only APPROVED observations with healthy evidence may support numeric conclusions."}
