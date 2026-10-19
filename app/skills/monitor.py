import json
import os
import re
from contextlib import contextmanager

from app.database import now, uid
from app.skills.compare import compare
from app.skills.market_data import extract_observations
from app.skills.source_reader import digest, normalize, read_source, registry


@contextmanager
def monitor_lock(store):
    path = store.path.with_suffix(".monitor.lock")
    with path.open("a+b") as handle:
        handle.seek(0)
        handle.write(b"0")
        handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError("A market check is already running. Open Monitor to follow its progress.") from None
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def register_sources(store, sources):
    for source in sources:
        store.execute("""INSERT INTO sources(id,name,url,kind,config) VALUES (?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET name=excluded.name,url=excluded.url,kind=excluded.kind,config=excluded.config""",
            (source["id"], source["name"], source["url"], source.get("type", "research"), json.dumps(source)))


def classify_event(doc, source):
    # Only explicit primary announcement verbs produce event candidates. No inferred numeric details.
    title = doc["title"].lower()
    if source.get("type") == "research":
        return "New Market Research Report"
    if source.get("type") in {"planning", "news"}:
        if re.search(r"approves?|approved|approval", title) and "office" in title:
            return "Planning Approval"
        if "planning application" in title and "office" in title:
            return "Planning Application"
        for token, label in [("pre-let", "Pre-let"), ("lease", "New Lease"),
                             ("relocation", "Office Relocation"), ("refurbish", "Major Refurbishment")]:
            if token in title and "office" in title:
                return label
    return None


def save_document(store, doc, source):
    old = store.one("SELECT d.* FROM document_states st JOIN documents d ON d.id=st.document_id WHERE st.url=?", (doc["url"],))
    if not old:
        old = store.one("SELECT * FROM documents WHERE url=? AND status='SOURCE_VERIFIED' ORDER BY fetched_at DESC LIMIT 1", (doc["url"],))
    existing = store.one("SELECT * FROM documents WHERE url=? AND hash=?", (doc["url"], doc["hash"]))
    stamp = now()
    if old and old["hash"] == doc["hash"]:
        store.execute("INSERT OR REPLACE INTO document_states VALUES (?,?,?)", (doc["url"], old["id"], stamp))
        return None
    if existing and existing["status"] in {"REJECTED", "RETRACTED"}:
        return None  # Explicit rejection/retraction cannot be undone by a fresh fetch.
    if existing:
        with store.connection() as conn:
            conn.execute("UPDATE documents SET status='SUPERSEDED' WHERE url=? AND status='SOURCE_VERIFIED'", (doc["url"],))
            conn.execute("UPDATE documents SET status='SOURCE_VERIFIED',fetched_at=? WHERE id=?", (stamp, existing["id"]))
            conn.execute("INSERT OR REPLACE INTO document_states VALUES (?,?,?)", (doc["url"], existing["id"], stamp))
            conn.execute("INSERT INTO document_revisions VALUES (?,?,?,?,?)", (uid(), doc["url"], old["id"] if old else None, existing["id"], stamp))
        store.invalidate()
        return existing["id"]
    ident = uid()
    version = store.one("SELECT COALESCE(max(version),0)+1 n FROM documents WHERE url=?", (doc["url"],))["n"]
    with store.connection() as conn:
        if old:
            conn.execute("UPDATE documents SET status='SUPERSEDED' WHERE id=?", (old["id"],))
            conn.execute("UPDATE signals SET status='INVALIDATED' WHERE document_id=?", (old["id"],))
        conn.execute("""INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ident, source["id"], doc["url"], doc["title"], doc["publisher"], doc.get("published_at"),
             stamp, stamp, doc["hash"], doc["raw_hash"], doc["raw_path"], doc["text"],
             old["id"] if old else None, version,
             doc.get("geography", ""), "SOURCE_VERIFIED", json.dumps(doc.get("pages", []))))
        conn.execute("INSERT INTO document_search VALUES (?,?,?)", (ident, doc["title"], doc["text"]))
        conn.execute("INSERT OR REPLACE INTO document_states VALUES (?,?,?)", (doc["url"], ident, stamp))
        conn.execute("INSERT INTO document_revisions VALUES (?,?,?,?,?)", (uid(), doc["url"], old["id"] if old else None, ident, stamp))
        for obs in extract_observations(doc, source):
            conn.execute("""INSERT OR IGNORE INTO observations
                (id,document_id,metric,geography,period,value,unit,definition,publisher,evidence_text,page,review_status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (obs["id"], ident, obs["metric"], obs["geography"],
                obs["period"], obs["value"], obs["unit"], obs["definition"], obs["publisher"],
                obs["evidence_text"], obs["page"], obs["review_status"]))
    store.audit("SOURCE_ACCESSED", ident, {"policy": doc.get("access"), "hash": doc["hash"]})
    store.invalidate()
    return ident


def create_metric_signals(store, run_id):
    rows = store.query("""SELECT o.*,d.source_id FROM observations o JOIN documents d ON d.id=o.document_id
        JOIN sources s ON s.id=d.source_id WHERE o.review_status='APPROVED'
        AND d.status='SOURCE_VERIFIED' AND s.status='HEALTHY' ORDER BY o.period""")
    count = 0
    previous = {}
    for obs in rows:
        key = tuple(obs[k] for k in ("metric", "geography", "unit", "definition", "publisher"))
        old = previous.get(key)
        previous[key] = obs
        if not old:
            continue
        result = compare(old, obs)
        if result["status"] != "COMPARABLE" or result["delta"] == 0:
            continue
        threshold = store.setting("vacancy_threshold_pp", 0.2) if obs["unit"] == "percent" else None
        high = abs(result["delta"]) >= threshold if threshold else abs(result["relative_percent"] or 0) >= 5
        count += store.execute("""INSERT OR IGNORE INTO signals VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (uid(), run_id, obs["document_id"], obs["id"], old["id"], "METRIC_CHANGE",
             "HIGH" if high else "MEDIUM", f"{obs['geography']} {obs['metric']}: {result['delta']:+g} {result['delta_unit']}",
             json.dumps(result), "ACTIVE", now()))
    return count


def run_monitor(store, trigger="once", *, sources=None, reader=None, generate=True):
    reader = reader or (lambda source: read_source(source, store.path.parent))
    sources = [s for s in (sources if sources is not None else registry()) if s.get("enabled", True)]
    with monitor_lock(store):
        baseline = not bool(store.one("SELECT id FROM monitor_runs WHERE status IN ('SUCCESS','PARTIAL') LIMIT 1"))
        ident = uid()
        store.execute("""INSERT INTO monitor_runs(id,trigger,started_at,status,phase,source_count,baseline)
            VALUES (?,?,?,'RUNNING','Collecting sources',?,?)""", (ident, trigger, now(), len(sources), int(baseline)))
        register_sources(store, sources)
        success = documents = events = 0
        errors = []
        try:
            for source in sources:
                store.execute("UPDATE sources SET last_attempt=? WHERE id=?", (now(), source["id"]))
                try:
                    docs = reader(source)
                    for doc in docs:
                        doc_id = save_document(store, doc, source)
                        is_new = bool(doc_id)
                        if is_new:
                            documents += 1
                        else:
                            doc_id = store.one("SELECT id FROM documents WHERE url=? AND hash=?", (doc["url"], doc["hash"]))["id"]
                        kind = classify_event(doc, source)
                        if kind:
                            # Entity+type+publication identity supplements canonical URL and body dedupe.
                            entity = digest(normalize(doc["title"].lower()) + kind + str(doc.get("published_at")))
                            event_id = uid()
                            same_document_event = store.one("SELECT id FROM events WHERE document_id=? AND event_type=? AND status='SOURCE_VERIFIED'", (doc_id,kind))
                            added = 0 if same_document_event else store.execute("INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?,?,?,?)",
                                (event_id, doc_id, doc["title"], kind, doc.get("geography", ""),
                                 doc.get("published_at"), now(), doc["text"][:500], entity, "SOURCE_VERIFIED"))
                            events += added
                        if not is_new:
                            continue
                        store.execute("INSERT INTO signals VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (uid(), ident, doc_id, None, None, "SOURCE_UPDATE", "INFO",
                             "Baseline source discovered" if baseline else "Source update requires market review",
                             json.dumps({"title": doc["title"], "url": doc["url"], "event_candidate": kind}), "ACTIVE", now()))
                    store.execute("UPDATE sources SET status='HEALTHY',last_success=?,error=NULL WHERE id=?", (now(), source["id"]))
                    success += 1
                except Exception as exc:
                    # Do not store provider bodies, authentication headers or arbitrary tracebacks.
                    message = f"{source['name']}: {type(exc).__name__}"
                    if isinstance(exc, ValueError):
                        message += ": " + str(exc)[:200]
                    errors.append(message)
                    store.execute("UPDATE sources SET status='FETCH_FAILED',error=? WHERE id=?", (message, source["id"]))
            store.execute("UPDATE monitor_runs SET phase='Comparing updates and validating evidence' WHERE id=?", (ident,))
            store.invalidate()
            signals = create_metric_signals(store, ident)
            status = "SUCCESS" if success == len(sources) and success else ("PARTIAL" if success else "FAILED")
            store.execute("""UPDATE monitor_runs SET status=?,phase='Preparing briefing',success_count=?,
                new_documents=?,new_events=?,valid_signals=?,error=? WHERE id=?""",
                (status, success, documents, events, signals, "; ".join(errors) or None, ident))
            if generate:
                from app.skills.report import make_report
                from app.services.notifications import dispatch
                analysis_id = None
                if not baseline and (events or signals):
                    if store.setting("model_block"):
                        store.audit("AI_ANALYSIS_SKIPPED", ident, {"reason": "Official provider is blocked; evidence retained."})
                    else:
                        from app.agent import ask
                        store.execute("UPDATE monitor_runs SET phase='Generating evidence-constrained analysis' WHERE id=?", (ident,))
                        analysis = ask(store, "Analyze newly discovered London office evidence from the latest monitor. Read sources and distinguish facts, interpretations and missing coverage. Do not run another monitor. Do not publish pending numbers.")
                        analysis_id = analysis["agent_run_id"]
                report = make_report(store, ident, agent_run_id=analysis_id)
                deliveries = dispatch(store, report["id"])
                store.execute("UPDATE monitor_runs SET report_id=?,notification_status=? WHERE id=?",
                              (report["id"], json.dumps(deliveries), ident))
            store.execute("UPDATE monitor_runs SET phase='Completed',finished_at=? WHERE id=?", (now(), ident))
        except Exception as exc:
            store.execute("UPDATE monitor_runs SET status='FAILED',phase='Failed',finished_at=?,error=? WHERE id=?",
                          (now(), type(exc).__name__, ident))
            raise
        return store.one("SELECT * FROM monitor_runs WHERE id=?", (ident,))


def review_observation(store, ident, status, reviewer, reason):
    if status not in {"APPROVED", "REJECTED", "RETRACTED"} or not reviewer.strip() or not reason.strip():
        raise ValueError("Explicit status, reviewer and reason are required.")
    row = store.one("SELECT o.*,d.text,d.status doc_status FROM observations o JOIN documents d ON d.id=o.document_id WHERE o.id=?", (ident,))
    if not row:
        raise ValueError("Observation not found.")
    if status == "APPROVED" and (not row["evidence_text"] or row["evidence_text"] not in row["text"] or row["doc_status"] != "SOURCE_VERIFIED"):
        raise ValueError("Approval requires an exact source quote and current source evidence.")
    store.execute("UPDATE observations SET review_status=?,reviewer=?,review_reason=?,reviewed_at=? WHERE id=?",
                  (status, reviewer, reason, now(), ident))
    store.audit("HUMAN_REVIEW", ident, {"status": status, "reviewer": reviewer, "reason": reason})
    store.invalidate()
