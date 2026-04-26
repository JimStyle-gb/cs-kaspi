from __future__ import annotations
def run(products: list[dict], existing: list[dict]) -> list[dict]:
    for p in products:
        p.setdefault("kaspi_match",{"exists_in_kaspi":False,"match_status":"not_matched","kaspi_product_id":None,"match_confidence":"none"})
    return products
