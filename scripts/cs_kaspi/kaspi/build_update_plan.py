from __future__ import annotations
from scripts.cs_kaspi.core.time_utils import now_iso
def run(products: list[dict]) -> dict:
    return {"built_at":now_iso(),"count":0,"products":[]}
