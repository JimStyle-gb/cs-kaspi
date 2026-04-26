from __future__ import annotations

import math
import re
from typing import Any

from scripts.cs_kaspi.core.time_utils import now_iso
from .utils import fetch_html, make_soup, save_text, category_dirs, normalize_text


def _detect_total_products(soup) -> int | None:
    result = soup.select_one(".woocommerce-result-count")
    if not result:
        return None
    text = normalize_text(result.get_text(" ", strip=True))
    match = re.search(r"из\s+(\d+)", text)
    return int(match.group(1)) if match else None


def run(categories_payload: dict[str, Any]) -> dict[str, Any]:
    dirs = category_dirs()
    pages: list[dict[str, Any]] = []
    for category in categories_payload.get("categories", []):
        root_url = category["category_url"].rstrip("/") + "/"
        first_html = fetch_html(root_url)
        first_soup = make_soup(first_html)
        total_products = _detect_total_products(first_soup)
        total_pages = max(1, math.ceil(total_products / 50)) if total_products else 1

        for page in range(1, total_pages + 1):
            page_url = root_url if page == 1 else f"{root_url}page/{page}/"
            html_text = first_html if page == 1 else fetch_html(page_url)
            filename = f"{category['category_key']}_page_{page}.html"
            save_text(dirs["catalog_pages"] / filename, html_text)
            pages.append({
                "supplier_category_name": category["supplier_category_name"],
                "category_key": category["category_key"],
                "page_number": page,
                "page_url": page_url,
                "saved_path": str(dirs["catalog_pages"] / filename),
            })

    return {
        "supplier_key": "demiand",
        "fetched_at": now_iso(),
        "catalog_pages_count": len(pages),
        "pages": pages,
    }
