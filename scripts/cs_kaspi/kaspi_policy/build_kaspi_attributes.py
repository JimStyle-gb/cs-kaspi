from __future__ import annotations


def run(product: dict) -> dict[str, str]:
    official = product.get("official", {})
    specs = official.get("specs") or official.get("specs_raw") or {}
    return {str(k): str(v) for k, v in specs.items() if v is not None}
