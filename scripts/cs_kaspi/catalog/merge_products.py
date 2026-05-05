from __future__ import annotations

from copy import deepcopy
from typing import Any

from scripts.cs_kaspi.core.text_utils import slugify_ascii


def run(official_states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    seen: set[str] = set()

    for state in official_states:
        for product in state.get("products", []):
            row = deepcopy(product)
            key = slugify_ascii(row.get("product_key"))
            if not key:
                continue
            row["product_key"] = key
            if key in seen:
                row.setdefault("quality", {})["duplicate_product_key"] = True
                key = f"{key}__dup_{len(seen) + 1}"
                row["product_key"] = key
            seen.add(key)
            products.append(row)
    return products
