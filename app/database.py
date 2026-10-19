import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.config import config


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return uuid.uuid4().hex


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS sources (
 id TEXT PRIMARY KEY, name TEXT, url TEXT, kind TEXT, config TEXT,
 status TEXT DEFAULT 'NOT_CHECKED', last_success TEXT, last_attempt TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS documents (
 id TEXT PRIMARY KEY, source_id TEXT REFERENCES sources(id), url TEXT, title TEXT,
 publisher TEXT, published_at TEXT, discovered_at TEXT, fetched_at TEXT, hash TEXT,
 raw_hash TEXT, raw_path TEXT, text TEXT, previous_id TEXT, version INTEGER,
 geography TEXT, status TEXT DEFAULT 'SOURCE_VERIFIED', pages TEXT,
 UNIQUE(url,hash));
CREATE VIRTUAL TABLE IF NOT EXISTS document_search USING fts5(id UNINDEXED,title,text);
CREATE TABLE IF NOT EXISTS observations (
 id TEXT PRIMARY KEY, document_id TEXT REFERENCES documents(id), metric TEXT,
 geography TEXT, period TEXT, value REAL, unit TEXT, definition TEXT, publisher TEXT,
 evidence_text TEXT, page INTEGER, review_status TEXT DEFAULT 'PENDING_REVIEW',
 reviewer TEXT, review_reason TEXT, reviewed_at TEXT,
 UNIQUE(document_id,metric,geography,period,definition,value));
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, document_id TEXT, title TEXT, event_type TEXT, geography TEXT,
 published_at TEXT, discovered_at TEXT, evidence_text TEXT, entity_key TEXT UNIQUE,
 status TEXT DEFAULT 'SOURCE_VERIFIED');
CREATE TABLE IF NOT EXISTS monitor_runs (
 id TEXT PRIMARY KEY, trigger TEXT, started_at TEXT, finished_at TEXT, status TEXT,
 phase TEXT, source_count INTEGER DEFAULT 0, success_count INTEGER DEFAULT 0,
 new_documents INTEGER DEFAULT 0, new_events INTEGER DEFAULT 0,
 valid_signals INTEGER DEFAULT 0, report_id TEXT, notification_status TEXT,
 error TEXT, baseline INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS signals (
 id TEXT PRIMARY KEY, run_id TEXT, document_id TEXT, observation_id TEXT,
 previous_observation_id TEXT, kind TEXT, priority TEXT, summary TEXT, detail TEXT,
 status TEXT DEFAULT 'ACTIVE', created_at TEXT, UNIQUE(kind,observation_id,previous_observation_id));
CREATE TABLE IF NOT EXISTS reports (
 id TEXT PRIMARY KEY, run_id TEXT, type TEXT, created_at TEXT, data TEXT,
 html_path TEXT, email_path TEXT, pdf_path TEXT);
CREATE TABLE IF NOT EXISTS notifications (
 id TEXT PRIMARY KEY, report_id TEXT, channel TEXT, recipient TEXT, status TEXT,
 attempt INTEGER, response TEXT, message_id TEXT, updated_at TEXT,
 UNIQUE(report_id,channel,recipient));
CREATE TABLE IF NOT EXISTS conversations (
 id TEXT PRIMARY KEY, created_at TEXT, updated_at TEXT, messages TEXT);
CREATE TABLE IF NOT EXISTS conversation_owners (
 conversation_id TEXT PRIMARY KEY, owner TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agent_runs (
 id TEXT PRIMARY KEY, conversation_id TEXT, question TEXT, started_at TEXT,
 finished_at TEXT, status TEXT, output TEXT, trace TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS model_calls (
 id TEXT PRIMARY KEY, at TEXT, model TEXT, status TEXT, reserved_tokens INTEGER,
 input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0, latency REAL,
 error TEXT);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value TEXT);
CREATE TABLE IF NOT EXISTS schedule_slots (
 slot TEXT PRIMARY KEY, claimed_at TEXT, run_id TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS audit_log (
 id TEXT PRIMARY KEY, at TEXT, action TEXT, subject TEXT, detail TEXT);
CREATE INDEX IF NOT EXISTS docs_source ON documents(source_id,fetched_at);
CREATE INDEX IF NOT EXISTS obs_key ON observations(metric,geography,period,review_status);
CREATE INDEX IF NOT EXISTS events_time ON events(discovered_at);
CREATE TABLE IF NOT EXISTS document_states (
 url TEXT PRIMARY KEY, document_id TEXT, checked_at TEXT);
CREATE TABLE IF NOT EXISTS document_revisions (
 id TEXT PRIMARY KEY, url TEXT, previous_document_id TEXT, document_id TEXT, detected_at TEXT);
"""


class Store:
    def __init__(self, path=None):
        self.path = Path(path or config().data / "market.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def query(self, sql, params=()):
        with self.connection() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql, params=()):
        with self.connection() as conn:
            return conn.execute(sql, params).rowcount

    def setting(self, key, default=None):
        row = self.one("SELECT value FROM settings WHERE key=?", (key,))
        return json.loads(row["value"]) if row else default

    def set_setting(self, key, value):
        self.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value)))

    def audit(self, action, subject, detail):
        self.execute("INSERT INTO audit_log VALUES (?,?,?,?,?)",
                     (uid(), now(), action, subject, json.dumps(detail)))

    def invalidate(self):
        self.execute("""UPDATE signals SET status='INVALIDATED' WHERE status='ACTIVE' AND (
            document_id IN (SELECT d.id FROM documents d JOIN sources s ON s.id=d.source_id
              WHERE d.status!='SOURCE_VERIFIED' OR s.status='FETCH_FAILED')
            OR observation_id IN (SELECT id FROM observations WHERE review_status!='APPROVED')
            OR previous_observation_id IN (SELECT o.id FROM observations o
              LEFT JOIN documents d ON d.id=o.document_id LEFT JOIN sources s ON s.id=d.source_id
              WHERE o.review_status!='APPROVED' OR d.status!='SOURCE_VERIFIED' OR s.status='FETCH_FAILED'))""")
