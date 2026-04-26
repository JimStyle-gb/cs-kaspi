from __future__ import annotations
from scripts.cs_kaspi.core.time_utils import now_iso

def run(parsed: list[dict]) -> dict:
    return {"checked_at":now_iso(),"checked_products":len(parsed),"found_products":sum(1 for x in parsed if x.get("found")),"errors":0}
