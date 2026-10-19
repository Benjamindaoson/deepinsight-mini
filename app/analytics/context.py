"""Typed BI drill-down context; no evidence approval or execution permission."""

import re
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.analytics.engine import QuerySpec

AREAS = ["Canary Wharf", "Central London", "City Fringe", "West End", "Midtown", "Fringe", "City", "UK"]


class MarketContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    geography: str | None = Field(default=None, max_length=100)
    metric: str | None = Field(default=None, max_length=60)
    period: str | None = Field(default=None, max_length=10)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def valid_scope(self):
        if self.geography is not None and self.geography not in AREAS:
            raise ValueError("Unsupported selected submarket")
        QuerySpec(metric=self.metric)
        if self.period and not re.fullmatch(
            r"20\d{2}(?:Q[1-4]|H[12]|M(?:0[1-9]|1[0-2])|-\d{2}-\d{2})?", self.period
        ):
            raise ValueError("Invalid selected observation period")
        if any(len(identity) > 120 for identity in self.evidence_ids):
            raise ValueError("Invalid evidence identity")
        return self


def resolve_context(store, question, conversation_id, provided=None):
    saved = store.setting("conversation_scope:" + conversation_id, {})
    selected = MarketContext.model_validate(provided or saved or {}).model_dump()
    explicit = next((geo for geo in AREAS if re.search(r"\b" + re.escape(geo) + r"\b", question, re.I)), None)
    if explicit and explicit != selected.get("geography"):
        selected["geography"] = explicit
        selected["evidence_ids"] = []
    match = re.search(r"\b(20\d{2})\s*Q([1-4])\b|\bQ([1-4])\s*(20\d{2})\b", question, re.I)
    if match:
        selected["period"] = (match[1] + "Q" + match[2]) if match[1] else (match[4] + "Q" + match[3])
    for metric, pattern in [
        ("vacancy_rate", r"vacancy"),
        ("availability", r"availability|available area"),
        ("take_up", r"take.up|leasing activity"),
        ("prime_rent", r"prime rent"),
        ("grade_a_rent", r"grade\s*a\s*rent"),
    ]:
        if re.search(pattern, question, re.I):
            selected["metric"] = metric
            break
    retained = []
    for identity in selected["evidence_ids"]:
        row = store.one("SELECT id FROM documents WHERE id=? AND status='SOURCE_VERIFIED'", (identity,))
        if not row:
            raise ValueError("SELECTED_EVIDENCE_NOT_CURRENT")
        retained.append(identity)
    selected["evidence_ids"] = retained
    if any(selected.get(k) for k in ["geography", "metric", "period", "evidence_ids"]):
        store.set_setting("conversation_scope:" + conversation_id, selected)
    return selected
