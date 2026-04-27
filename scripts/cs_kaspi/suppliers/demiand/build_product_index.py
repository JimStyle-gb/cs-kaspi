from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.hash_utils import stable_hash
from scripts.cs_kaspi.core.json_io import write_json
from scripts.cs_kaspi.core.time_utils import now_iso

from .utils import build_product_key, state_paths


def run(parsed_catalog_payload: dict[str, Any]) -> dict[str, Any]:
    dedup: dict[str, dict[str, Any]] = {}

    for item in parsed_catalog_payload.get("items", []):
        listing = item["listing"]
        url = listing["product_url"]
        product_key = build_product_key(item["category_key"], listing.get("slug") or listing.get("title_listing"))
        entry = {
            "product_key": product_key,
            "supplier_key": "demiand",
            "supplier_category_name": item["supplier_category_name"],
            "category_key": item["category_key"],
            "listing": {
                **listing,
                "listing_hash": stable_hash({
                    "url": listing.get("product_url"),
                    "title": listing.get("title_listing"),
                    "price": listing.get("price_listing"),
                    "old_price": listing.get("old_price_listing"),
                    "image": listing.get("image_preview"),
                }),
            },
            "identity": {
                "brand_guess": "DEMIAND",
                "model_guess": listing.get("slug"),
                "variant_guess": None,
            },
            "meta": {
                "first_seen_at": now_iso(),
                "last_seen_at": now_iso(),
                "is_active_in_catalog": True,
            },
        }
        dedup[url] = entry

    state = {
        "meta": {
            "supplier_key": "demiand",
            "built_at": now_iso(),
            "products_count": len(dedup),
        },
        "products": list(dedup.values()),
    }
    write_json(state_paths()["product_index"], state)
    return state
