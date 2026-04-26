from __future__ import annotations
from scripts.cs_kaspi.core.time_utils import now_iso

def run(products: list[dict], suppliers: list[str], categories: list[str]) -> dict:
    return {"meta":{"project_name":"CS-Kaspi","built_at":now_iso(),"official_sources_checked_at":now_iso(),"market_sources_checked_at":None,"total_products":len(products),"suppliers":suppliers,"categories":categories},"products":products}
