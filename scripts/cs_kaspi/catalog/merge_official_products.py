from __future__ import annotations
def run(supplier_products: list[list[dict]]) -> list[dict]:
    merged=[]
    for batch in supplier_products:
        merged.extend(batch or [])
    return merged
