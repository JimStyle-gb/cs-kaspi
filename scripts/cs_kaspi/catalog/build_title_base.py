from __future__ import annotations
def run(product: dict) -> str:
    return product.get("official",{}).get("title","")
