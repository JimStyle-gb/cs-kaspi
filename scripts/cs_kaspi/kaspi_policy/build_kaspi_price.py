from __future__ import annotations
def run(product: dict) -> int | None:
    for value in [product.get("market",{}).get("ozon",{}).get("price"), product.get("market",{}).get("wb",{}).get("price")]:
        if isinstance(value,int) and value>0:
            return value
    return None
