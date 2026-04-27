from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.time_utils import now_iso

from .build_product_index import run as build_product_index
from .fetch_catalog_pages import run as fetch_catalog_pages
from .fetch_categories import run as fetch_categories
from .fetch_manuals import run as fetch_manuals
from .fetch_product_pages import run as fetch_product_pages
from .normalize_official import run as normalize_official
from .parse_category_pages import run as parse_category_pages
from .parse_manuals import run as parse_manuals
from .parse_product_pages import run as parse_product_pages


def run() -> dict[str, Any]:
    categories_payload = fetch_categories()
    catalog_payload = fetch_catalog_pages(categories_payload)
    parsed_catalog_payload = parse_category_pages(catalog_payload)
    product_index_state = build_product_index(parsed_catalog_payload)
    product_pages_payload = fetch_product_pages(product_index_state)
    parsed_products_payload = parse_product_pages(product_pages_payload)
    manuals_payload = fetch_manuals()
    parsed_manuals_payload = parse_manuals(manuals_payload)
    normalized_payload = normalize_official(parsed_products_payload)

    failed_count = product_pages_payload.get("failed_count", 0)
    return {
        "supplier_key": "demiand",
        "checked_at": now_iso(),
        "catalog_ok": failed_count == 0,
        "categories_found": categories_payload.get("categories_count", 0),
        "catalog_pages_fetched": catalog_payload.get("catalog_pages_count", 0),
        "products_found": product_index_state.get("meta", {}).get("products_count", 0),
        "product_pages_fetched": product_pages_payload.get("product_pages_count", 0),
        "product_pages_failed": failed_count,
        "products_parsed": parsed_products_payload.get("meta", {}).get("products_count", 0),
        "products_normalized": normalized_payload.get("meta", {}).get("products_count", 0),
        "manuals_found": len(manuals_payload.get("manuals", [])),
        "manuals_parsed": parsed_manuals_payload.get("manuals_count", 0),
        "errors": failed_count,
    }
