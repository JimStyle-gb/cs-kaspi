from __future__ import annotations
from scripts.cs_kaspi.core.time_utils import now_iso

def run(master_catalog: dict) -> dict:
    products=[]
    for p in master_catalog.get("products",[]):
        products.append({
            "product_key":p.get("product_key"),
            "supplier_key":p.get("supplier_key"),
            "category_key":p.get("category_key"),
            "official_title":p.get("official",{}).get("title"),
            "kaspi_title":p.get("kaspi_policy",{}).get("title"),
            "market_sellable":p.get("market",{}).get("sellable"),
            "kaspi_price":p.get("kaspi_policy",{}).get("price"),
            "kaspi_available":p.get("kaspi_policy",{}).get("available"),
            "lifecycle_status":p.get("status",{}).get("lifecycle_status"),
            "action_status":p.get("status",{}).get("action_status"),
            "needs_review":p.get("status",{}).get("needs_review"),
        })
    return {"built_at":now_iso(),"products":products}
