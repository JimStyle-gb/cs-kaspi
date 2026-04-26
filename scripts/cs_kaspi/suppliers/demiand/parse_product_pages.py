from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.time_utils import now_iso
from scripts.cs_kaspi.core.write_json import write_json
from scripts.cs_kaspi.core.hashing import stable_hash
from .utils import make_soup, normalize_text, parse_price_to_number, extract_json_ld, supplier_state_paths


def _extract_meta_value(text: str, label: str) -> str | None:
    marker = f"{label}:"
    if marker not in text:
        return None
    value = text.split(marker, 1)[1].split("Категории:", 1)[0].split("Метка:", 1)[0].strip()
    return normalize_text(value)


def _extract_categories(text: str) -> list[str]:
    if "Категории:" not in text:
        return []
    tail = text.split("Категории:", 1)[1].split("Метка:", 1)[0]
    return [normalize_text(x) for x in tail.split(",") if normalize_text(x)]


def run(product_pages_payload: dict[str, Any]) -> dict[str, Any]:
    products: list[dict[str, Any]] = []

    for page in product_pages_payload.get("pages", []):
        html_text = Path(page["saved_path"]).read_text(encoding="utf-8")
        soup = make_soup(html_text)

        title = normalize_text(soup.select_one("h1").get_text(" ", strip=True) if soup.select_one("h1") else None)
        meta_text = normalize_text(soup.select_one(".product_meta").get_text(" ", strip=True) if soup.select_one(".product_meta") else None)
        short_desc_tag = soup.select_one(".woocommerce-product-details__short-description")
        short_desc = normalize_text(short_desc_tag.get_text(" ", strip=True) if short_desc_tag else None)
        description_tag = soup.select_one("#tab-description, .woocommerce-Tabs-panel--description")
        description_text = normalize_text(description_tag.get_text(" ", strip=True) if description_tag else None)
        current_price_tag = soup.select_one(".summary .price ins .woocommerce-Price-amount, .summary .price .woocommerce-Price-amount")
        old_price_tag = soup.select_one(".summary .price del .woocommerce-Price-amount")

        attrs: dict[str, str] = {}
        for row in soup.select("table.woocommerce-product-attributes tr"):
            key_tag = row.select_one("th")
            value_tag = row.select_one("td")
            key = normalize_text(key_tag.get_text(" ", strip=True) if key_tag else None)
            value = normalize_text(value_tag.get_text(" ", strip=True) if value_tag else None)
            if key:
                attrs[key] = value

        images: list[str] = []
        for tag in soup.select(".woocommerce-product-gallery a, .wd-product-gallery a"):
            href = tag.get("href")
            if href and href not in images:
                images.append(href)
        if not images:
            for img in soup.select(".woocommerce-product-gallery img"):
                src = img.get("src") or img.get("data-large_image")
                if src and src not in images:
                    images.append(src)

        json_ld = extract_json_ld(soup)
        product_graph = next((item for item in json_ld if item.get("@type") == "Product"), {})
        offers = product_graph.get("offers") if isinstance(product_graph.get("offers"), dict) else {}
        breadcrumbs = [normalize_text(x.get_text(" ", strip=True)) for x in soup.select(".woocommerce-breadcrumb a, .woocommerce-breadcrumb span") if normalize_text(x.get_text(" ", strip=True))]
        categories = _extract_categories(meta_text or "")

        product = {
            "product_key": page["product_key"],
            "supplier_key": "demiand",
            "supplier_category_name": categories[0] if categories else None,
            "category_key": None,
            "brand": "DEMIAND",
            "model_key": None,
            "variant_key": None,
            "official": {
                "exists": True,
                "status": "active",
                "product_id": _extract_meta_value(meta_text or "", "Артикул") or product_graph.get("sku"),
                "url": page["product_url"],
                "slug": Path(page["product_url"].rstrip('/')).name,
                "title_official": title,
                "short_description": short_desc,
                "description_official": description_text,
                "price": parse_price_to_number(current_price_tag.get_text(" ", strip=True) if current_price_tag else None) or product_graph.get("offers", {}).get("price"),
                "old_price": parse_price_to_number(old_price_tag.get_text(" ", strip=True) if old_price_tag else None),
                "currency": "RUB",
                "available": True if offers.get("availability", "").endswith("InStock") else None,
                "images": images,
                "specs_raw": attrs,
                "package": {
                    "raw_text": short_desc,
                },
                "breadcrumbs": breadcrumbs,
                "json_ld": product_graph,
                "checked_at": now_iso(),
                "source_hash": "",
            },
            "meta": {
                "parsed_ok": True,
                "parse_errors": [],
                "first_seen_at": now_iso(),
                "last_seen_at": now_iso(),
            },
        }
        product["official"]["source_hash"] = stable_hash(product["official"])
        products.append(product)

    state = {
        "meta": {
            "supplier_key": "demiand",
            "built_at": now_iso(),
            "products_count": len(products),
            "errors_count": 0,
        },
        "products": products,
    }
    write_json(supplier_state_paths()["official_products"], state)
    return state
