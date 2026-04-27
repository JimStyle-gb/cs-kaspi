from __future__ import annotations

from typing import Any

import requests

from scripts.cs_kaspi.core.time_utils import now_iso
from .utils import fetch_html, save_text, category_dirs, get_supplier_config


def run(product_index_payload: dict[str, Any]) -> dict[str, Any]:
    dirs = category_dirs()
    cfg = get_supplier_config()
    timeout = cfg.get("fetch_rules", {}).get("request_timeout_seconds", 60)

    pages: list[dict[str, Any]] = []
    failed_pages: list[dict[str, Any]] = []

    for product in product_index_payload.get("products", []):
        url = product["listing"]["product_url"]
        filename = f"{product['product_key']}.html"
        save_path = dirs["product_pages"] / filename
        try:
            html_text = fetch_html(url, timeout=timeout)
            save_text(save_path, html_text)
            pages.append({
                "product_key": product["product_key"],
                "product_url": url,
                "saved_path": str(save_path),
            })
        except requests.RequestException as exc:
            failed_pages.append({
                "product_key": product["product_key"],
                "product_url": url,
                "error": str(exc),
            })

    return {
        "supplier_key": "demiand",
        "fetched_at": now_iso(),
        "product_pages_count": len(pages),
        "failed_count": len(failed_pages),
        "pages": pages,
        "failed_pages": failed_pages,
    }
