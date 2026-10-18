import math
import re


def period_key(period):
    match = re.fullmatch(r"(20\d{2})(Q[1-4]|H[12]|M(?:0[1-9]|1[0-2]))?", period or "")
    if not match:
        return None
    year, part = match.groups()
    return (part[0] if part else "Y", int(year), int(part[1:]) if part else 0)


def compare(old, new):
    def refuse(reason):
        return {"status": "NOT_COMPARABLE", "reason": reason}
    for item in (old, new):
        if item.get("review_status") != "APPROVED":
            return refuse("Both observations require explicit approval.")
        if not isinstance(item.get("value"), (float, int)) or not math.isfinite(item["value"]):
            return refuse("A finite numeric value is required.")
    for field in ("metric", "geography", "unit", "definition", "publisher"):
        if not old.get(field) or old[field] != new.get(field):
            return refuse(f"Incompatible {field}.")
    a, b = period_key(old.get("period")), period_key(new.get("period"))
    if not a or not b or a[0] != b[0] or b[1:] <= a[1:]:
        return refuse("Periods must be explicit, same frequency and increasing; revisions are not trends.")
    delta = new["value"] - old["value"]
    return {"status": "COMPARABLE", "delta": round(delta, 8),
            "delta_unit": "percentage points" if old["unit"] == "percent" else old["unit"],
            "relative_percent": delta / old["value"] * 100 if old["value"] else None,
            "from_period": old["period"], "to_period": new["period"]}
