"""Bound the complete tool JSON envelope; never slice through a source record."""

import copy
import json


def pack_result(value, max_bytes=16000):
    result = copy.deepcopy(value)

    def encode(v):
        return json.dumps(v, ensure_ascii=True, separators=(",", ":")).encode()

    removed = False

    def lists(item):
        found = []
        if isinstance(item, dict):
            for key, child in item.items():
                if isinstance(child, list) and child and key != "evidence_ids":
                    found.append(child)
                elif isinstance(child, dict):
                    found += lists(child)
        return found

    def ids(item):
        found = set()
        if isinstance(item, dict):
            if item.get("document_id"):
                found.add(item["document_id"])
            if item.get("id") and item.get("url"):
                found.add(item["id"])
            for key, child in item.items():
                if key != "evidence_ids":
                    found |= ids(child)
        elif isinstance(item, list):
            for child in item:
                found |= ids(child)
        return found

    while len(encode(result)) > max_bytes:
        candidates = lists(result)
        if not candidates:
            return dict(
                status="PARTIAL",
                data=dict(error_code="TOOL_RESULT_TOO_LARGE"),
                evidence_ids=[],
                warnings=["Narrow the request; no oversized result or fabricated evidence is supplied."],
            )
        largest = max(candidates, key=lambda v: len(encode(v)))
        largest.pop()
        removed = True
        if "evidence_ids" in result:
            result["evidence_ids"] = [i for i in result["evidence_ids"] if i in ids(result)]
    if removed:
        result["retrieval_notice"] = (
            "Bounded subset: complete records omitted to fit context. Omission does not establish missing market coverage."
        )
        if len(encode(result)) > max_bytes:
            return pack_result(result, max_bytes - 250)
    return result
