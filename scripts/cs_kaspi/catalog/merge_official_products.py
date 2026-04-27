from __future__ import annotations

from copy import deepcopy


def run(supplier_products: list[list[dict]]) -> list[dict]:
    merged: list[dict] = []
    seen_keys: set[str] = set()

    for batch in supplier_products:
        for item in batch or []:
            row = deepcopy(item)
            product_key = str(row.get("product_key") or "").strip()
            if not product_key:
                continue
            if product_key in seen_keys:
                continue
            seen_keys.add(product_key)
            merged.append(row)

    return merged
