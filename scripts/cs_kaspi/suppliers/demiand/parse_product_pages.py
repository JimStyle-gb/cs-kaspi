from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.time_utils import now_iso
from scripts.cs_kaspi.core.write_json import write_json
from scripts.cs_kaspi.core.hashing import stable_hash
from .utils import make_soup, normalize_text, parse_price_to_number, extract_json_ld, supplier_state_paths, slug_from_url, get_supplier_config


def _clean_product_id(value: str | None) -> str | None:
    cleaned = normalize_text(value)
    if not cleaned:
        return None
    cleaned = re.split(r"Категори[яи]:|Метк[аи]:", cleaned, maxsplit=1)[0].strip()
    cleaned = cleaned.strip(" -,")
    return cleaned or None


def _extract_meta_value(meta_text: str, label: str) -> str | None:
    marker = f"{label}:"
    if marker not in meta_text:
        return None
    tail = meta_text.split(marker, 1)[1]
    tail = re.split(r"Категори[яи]:|Метк[аи]:", tail, maxsplit=1)[0]
    return _clean_product_id(tail)


def _extract_categories_from_meta(meta_text: str) -> list[str]:
    match = re.search(r"Категори[яи]:\s*(.+?)(?:Метк[аи]:|$)", meta_text)
    if not match:
        return []
    return [normalize_text(x) for x in match.group(1).split(",") if normalize_text(x)]


def _pick_available(soup, offers: dict[str, Any]) -> bool | None:
    availability = offers.get("availability") if isinstance(offers, dict) else None
    if isinstance(availability, str) and availability.endswith("InStock"):
        return True
    stock_tag = soup.select_one(".stock")
    stock_text = normalize_text(stock_tag.get_text(" ", strip=True) if stock_tag else None).lower()
    if "в наличии" in stock_text:
        return True
    if stock_text:
        return False
    return None


def run(product_pages_payload: dict[str, Any]) -> dict[str, Any]:
    mapping = get_supplier_config().get("category_mapping", {})
    products: list[dict[str, Any]] = []

    for page in product_pages_payload.get("pages", []):
        html_text = Path(page["saved_path"]).read_text(encoding="utf-8")
        soup = make_soup(html_text)

        title = normalize_text(soup.select_one("h1").get_text(" ", strip=True) if soup.select_one("h1") else None)
        meta_tag = soup.select_one(".product_meta")
        meta_text = normalize_text(meta_tag.get_text(" ", strip=True) if meta_tag else None)
        sku_tag = soup.select_one(".product_meta .sku, .sku_wrapper .sku")
        sku_value = _clean_product_id(sku_tag.get_text(" ", strip=True) if sku_tag else None)
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
                src = img.get("data-large_image") or img.get("src")
                if src and src not in images:
                    images.append(src)

        json_ld = extract_json_ld(soup)
        product_graph = next((item for item in json_ld if item.get("@type") == "Product"), {})
        offers = product_graph.get("offers") if isinstance(product_graph.get("offers"), dict) else {}
        breadcrumbs = [normalize_text(x.get_text(" ", strip=True)) for x in soup.select(".woocommerce-breadcrumb a, .woocommerce-breadcrumb span") if normalize_text(x.get_text(" ", strip=True))]
        categories = [normalize_text(x.get_text(" ", strip=True)) for x in soup.select(".product_meta .posted_in a") if normalize_text(x.get_text(" ", strip=True))]
        if not categories:
            categories = _extract_categories_from_meta(meta_text or "")
        supplier_category_name = page.get("supplier_category_name") or next((x for x in categories if x in mapping), None) or (categories[0] if categories else None)
        category_key = page.get("category_key") or mapping.get(supplier_category_name or "")
        product_id = sku_value or _extract_meta_value(meta_text or "", "Артикул") or _clean_product_id(product_graph.get("sku"))

        product = {
            "product_key": page["product_key"],
            "supplier_key": "demiand",
            "supplier_category_name": supplier_category_name,
            "category_key": category_key,
            "brand": "DEMIAND",
            "model_key": None,
            "variant_key": None,
            "official": {
                "exists": True,
                "status": "active",
                "product_id": product_id,
                "url": page["product_url"],
                "slug": slug_from_url(page["product_url"]),
                "title_official": title,
                "short_description": short_desc,
                "description_official": description_text,
                "price": parse_price_to_number(current_price_tag.get_text(" ", strip=True) if current_price_tag else None) or parse_price_to_number(str(offers.get("price"))) if offers else None,
                "old_price": parse_price_to_number(old_price_tag.get_text(" ", strip=True) if old_price_tag else None),
                "currency": "RUB",
                "available": _pick_available(soup, offers),
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
            "listing_snapshot": page.get("listing_snapshot", {}),
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
