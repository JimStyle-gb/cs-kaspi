from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from scripts.cs_kaspi.core.time_utils import now_iso
from .utils import get_supplier_config, fetch_html, make_soup, normalize_text, category_key_from_supplier_name, save_text, category_dirs


def run() -> dict[str, Any]:
    cfg = get_supplier_config()
    mapping = cfg.get("category_mapping", {})
    dirs = category_dirs()
    categories: list[dict[str, Any]] = []

    for root in cfg.get("category_roots", []):
        if not root.get("enabled", True):
            continue
        root_url = root["root_url"]
        html_text = fetch_html(root_url, timeout=cfg.get("fetch_rules", {}).get("request_timeout_seconds", 30))
        save_text(dirs["catalog_pages"] / "root_for_kitchen.html", html_text)
        soup = make_soup(html_text)

        found = False
        for link in soup.select(".product-categories a"):
            name = normalize_text(link.get_text(" ", strip=True))
            href = link.get("href")
            if not name or not href or name not in mapping:
                continue
            categories.append({
                "supplier_category_name": name,
                "category_key": category_key_from_supplier_name(name, mapping),
                "category_url": urljoin(root_url, href),
            })
            found = True

        if not found:
            categories.append({
                "supplier_category_name": root.get("supplier_category_name", "Товары для кухни"),
                "category_key": category_key_from_supplier_name(root.get("supplier_category_name", "for_kitchen"), mapping),
                "category_url": root_url,
            })

    # Deduplicate by URL.
    unique: dict[str, dict[str, Any]] = {item["category_url"]: item for item in categories}
    return {
        "supplier_key": "demiand",
        "fetched_at": now_iso(),
        "categories_count": len(unique),
        "categories": list(unique.values()),
    }
