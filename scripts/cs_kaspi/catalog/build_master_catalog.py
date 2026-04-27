from __future__ import annotations

from collections import Counter

from scripts.cs_kaspi.core.time_utils import now_iso


def run(products: list[dict], suppliers: list[str], categories: list[str]) -> dict:
    return {
        "meta": {
            "project_name": "CS-Kaspi",
            "built_at": now_iso(),
            "official_sources_checked_at": now_iso(),
            "market_sources_checked_at": None,
            "total_products": len(products),
            "suppliers": suppliers,
            "categories": categories,
        },
        "products": products,
    }


def build_summary(catalog: dict) -> dict:
    products = catalog.get("products", [])
    suppliers_counter = Counter(p.get("supplier_key") for p in products if p.get("supplier_key"))
    categories_counter = Counter(p.get("category_key") for p in products if p.get("category_key"))
    lifecycle_counter = Counter(
        (p.get("status") or {}).get("lifecycle_status", "unknown")
        for p in products
    )

    return {
        "built_at": catalog.get("meta", {}).get("built_at"),
        "total_products": len(products),
        "suppliers": dict(sorted(suppliers_counter.items())),
        "categories": dict(sorted(categories_counter.items())),
        "lifecycle_status": {
            "catalog_only": lifecycle_counter.get("catalog_only", 0),
            "market_active": lifecycle_counter.get("market_active", 0),
            "kaspi_ready": lifecycle_counter.get("kaspi_ready", 0),
            "kaspi_active": lifecycle_counter.get("kaspi_active", 0),
            "kaspi_paused": lifecycle_counter.get("kaspi_paused", 0),
            "needs_review": lifecycle_counter.get("needs_review", 0),
            "blocked": lifecycle_counter.get("blocked", 0),
        },
    }
