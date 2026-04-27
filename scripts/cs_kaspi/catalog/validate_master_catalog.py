from __future__ import annotations

from collections import Counter
from typing import Any

from scripts.cs_kaspi.core.paths import ROOT
from scripts.cs_kaspi.core.yaml_io import read_yaml


def run(products: list[dict[str, Any]]) -> dict[str, Any]:
    categories_cfg = read_yaml(ROOT / "config" / "categories.yml").get("categories", {})
    keys = [p.get("product_key") for p in products if p.get("product_key")]
    dupes = sorted([k for k, c in Counter(keys).items() if c > 1])

    problems: list[dict[str, Any]] = []
    for product in products:
        key = product.get("product_key")
        category_key = product.get("category_key")
        official = product.get("official", {})
        if not key:
            problems.append({"level": "critical", "product_key": key, "message": "missing product_key"})
        elif any(ord(ch) > 127 for ch in key):
            problems.append({"level": "critical", "product_key": key, "message": "non-ascii product_key"})
        if category_key not in categories_cfg:
            problems.append({"level": "critical", "product_key": key, "message": f"missing category config: {category_key}"})
        if not official.get("title_official"):
            problems.append({"level": "critical", "product_key": key, "message": "missing official.title_official"})
        if not official.get("url"):
            problems.append({"level": "critical", "product_key": key, "message": "missing official.url"})
        images = official.get("images") or []
        if "#" in images:
            problems.append({"level": "cosmetic", "product_key": key, "message": "bad image #"})

    for dupe in dupes:
        problems.append({"level": "critical", "product_key": dupe, "message": "duplicate product_key"})

    return {
        "total_products": len(products),
        "critical_count": sum(1 for p in problems if p["level"] == "critical"),
        "cosmetic_count": sum(1 for p in problems if p["level"] == "cosmetic"),
        "problems": problems,
    }
