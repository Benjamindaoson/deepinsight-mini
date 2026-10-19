import json


def test_tool_envelope_is_valid_json_and_retains_whole_evidence_records():
    from app.tools.packing import pack_result

    rows = [
        {"id": str(i), "document_id": "d" + str(i), "evidence_text": "Exact source quotation " + ("x" * 800)}
        for i in range(60)
    ]
    original = {
        "data": {"rows": rows},
        "evidence_ids": ["d" + str(i) for i in range(60)],
        "status": "SUCCESS",
    }
    packed = pack_result(original, 4000)
    assert len(json.dumps(packed).encode()) <= 4000
    assert packed["data"]["rows"] and len(packed["data"]["rows"]) < 60
    assert packed["data"]["rows"][0]["evidence_text"] == rows[0]["evidence_text"]
    assert set(packed["evidence_ids"]) == {r["document_id"] for r in packed["data"]["rows"]}
    assert len(original["data"]["rows"]) == 60
