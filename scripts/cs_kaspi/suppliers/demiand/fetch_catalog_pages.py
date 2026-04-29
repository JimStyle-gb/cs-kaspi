from __future__ import annotations

import math
import re
from typing import Any

from scripts.cs_kaspi.core.time_utils import now_iso
from scripts.cs_kaspi.core.text_utils import normalize_spaces

from .utils import fetch_html, input_dirs, make_soup, save_text


def _detect_total_products(soup) -> int | None:
    result = soup.select_one(".woocommerce-result-count")
    if not result:
        return None
    text = normalize_spaces(result.get_text(" ", strip=True))
    match = re.search(r"из\s+(\d+)", text)
    return int(match.group(1)) if match else None


def run(categories_payload: dict[str, Any]) -> dict[str, Any]:
    dirs = input_dirs()
    pages: list[dict[str, Any]] = []

    for category in categories_payload.get("categories", []):
        root_url = category["category_url"].rstrip("/") + "/"
        first_html = fetch_html(root_url)
        first_soup = make_soup(first_html)
        total_products = _detect_total_products(first_soup)
        total_pages = max(1, math.ceil(total_products / 50)) if total_products else 1

        for page_no in range(1, total_pages + 1):
            page_url = root_url if page_no == 1 else f"{root_url}page/{page_no}/"
            html_text = first_html if page_no == 1 else fetch_html(page_url)
            filename = f"{category['category_key']}_page_{page_no}.html"
            saved_path = dirs["catalog_pages"] / filename
            save_text(saved_path, html_text)
            pages.append({
                "supplier_category_name": category["supplier_category_name"],
                "category_key": category["category_key"],
                "page_number": page_no,
                "page_url": page_url,
                "saved_path": str(saved_path),
            })

    return {
        "supplier_key": "demiand",
        "fetched_at": now_iso(),
        "catalog_pages_count": len(pages),
        "pages": pages,
    }
