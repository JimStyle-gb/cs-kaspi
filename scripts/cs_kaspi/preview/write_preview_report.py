from __future__ import annotations
from scripts.cs_kaspi.core.time_utils import now_iso
def run(preview: dict) -> dict:
    return {"built_at":now_iso(),"total_products":len(preview.get("products",[]))}
