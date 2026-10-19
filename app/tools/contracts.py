import hashlib
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Empty(Input):
    pass


class DocumentInput(Input):
    document_id: str = Field(min_length=1, max_length=120)


class ReportInput(Input):
    report_id: str = Field(min_length=1, max_length=120)


class ToolResult(BaseModel):
    tool_name: str
    status: Literal["SUCCESS", "PARTIAL", "INSUFFICIENT_EVIDENCE", "NOT_COMPARABLE", "ERROR"]
    data: dict
    evidence_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    duration_ms: float


def document(store, identity):
    row = store.one(
        "SELECT d.*,s.status source_health FROM documents d JOIN sources s ON s.id=d.source_id WHERE d.id=?",
        (identity,),
    )
    if not row:
        raise ValueError("DOCUMENT_NOT_FOUND")
    if row["status"] != "SOURCE_VERIFIED" or row["source_health"] != "HEALTHY":
        raise ValueError("DOCUMENT_NOT_CURRENT")
    path = Path(row["raw_path"] or "")
    if (
        not path.is_file()
        or path.stat().st_size > 20_000_000
        or hashlib.sha256(path.read_bytes()).hexdigest() != row["raw_hash"]
    ):
        raise ValueError("ORIGINAL_HASH_MISMATCH")
    return row
