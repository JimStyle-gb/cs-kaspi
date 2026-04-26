from __future__ import annotations
def run(product: dict) -> dict[str,str]:
    specs=product.get("official",{}).get("specs",{})
    return {str(k):str(v) for k,v in specs.items() if v is not None}
