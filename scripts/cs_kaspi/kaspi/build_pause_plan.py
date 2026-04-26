from __future__ import annotations
from scripts.cs_kaspi.core.time_utils import now_iso
def run(products: list[dict]) -> dict:
    items=[{"product_key":p.get("product_key"),"reason":"market_not_found"} for p in products if p.get("status",{}).get("action_status")=="pause"]
    return {"built_at":now_iso(),"count":len(items),"products":items}
