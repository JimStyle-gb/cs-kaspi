from __future__ import annotations
def run(product: dict) -> list[str]:
    return list(product.get("official",{}).get("images",[]))
