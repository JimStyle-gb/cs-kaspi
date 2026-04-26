from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.time_utils import now_iso
from .utils import fetch_html, save_text, category_dirs


def run(product_index_payload: dict[str, Any]) -> dict[str, Any]:
    dirs = category_dirs()
    pages: list[dict[str, Any]] = []
    for product in product_index_payload.get("products", []):
        url = product["listing"]["product_url"]
        html_text = fetch_html(url)
        filename = f"{product['product_key']}.html"
        save_path = dirs["product_pages"] / filename
        save_text(save_path, html_text)
        pages.append({
            "product_key": product["product_key"],
            "product_url": url,
            "saved_path": str(save_path),
            "supplier_category_name": product.get("supplier_category_name"),
            "category_key": product.get("category_key"),
            "listing_snapshot": {
                "title_listing": product["listing"].get("title_listing"),
                "price_listing": product["listing"].get("price_listing"),
                "old_price_listing": product["listing"].get("old_price_listing"),
                "image_preview": product["listing"].get("image_preview"),
            },
        })
    return {
        "supplier_key": "demiand",
        "fetched_at": now_iso(),
        "product_pages_count": len(pages),
        "pages": pages,
    }
