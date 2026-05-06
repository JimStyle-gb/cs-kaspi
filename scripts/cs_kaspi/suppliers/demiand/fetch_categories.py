from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from scripts.cs_kaspi.core.time_utils import now_iso
from scripts.cs_kaspi.core.text_utils import normalize_spaces

from .utils import category_key_from_name, fetch_html, get_config, input_dirs, make_soup, save_text


def run() -> dict[str, Any]:
    cfg = get_config()
    dirs = input_dirs()
    categories: list[dict[str, Any]] = []

    for root in cfg.get("category_roots", []):
        if not root.get("enabled", True):
            continue
        root_url = root["root_url"]
        html_text = fetch_html(root_url)
        save_text(dirs["catalog_pages"] / "root_for_kitchen.html", html_text)
        soup = make_soup(html_text)

        found = False
        for link in soup.select(".product-categories a"):
            name = normalize_spaces(link.get_text(" ", strip=True))
            href = link.get("href")
            if not name or not href or name not in cfg.get("category_mapping", {}):
                continue
            categories.append({
                "supplier_category_name": name,
                "category_key": category_key_from_name(name),
                "category_url": urljoin(root_url, href),
            })
            found = True

        if not found:
            name = root.get("supplier_category_name", "Товары для кухни")
            categories.append({
                "supplier_category_name": name,
                "category_key": category_key_from_name(name),
                "category_url": root_url,
            })

    unique = {item["category_url"]: item for item in categories}
    return {
        "supplier_key": "demiand",
        "fetched_at": now_iso(),
        "categories_count": len(unique),
        "categories": list(unique.values()),
    }
