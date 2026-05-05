from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.text_utils import normalize_spaces
from scripts.cs_kaspi.core.time_utils import now_iso

from .utils import clean_images, make_soup, parse_price_to_number, slug_from_url


def _pick_preview_image(card) -> str | None:
    image = card.select_one("img")
    if not image:
        return None
    for attr in ("data-src", "data-lazy-src", "data-wood-src", "data-srcset", "src"):
        value = image.get(attr)
        if value and "lazy.svg" not in value:
            return value.split(",")[0].strip()
    return None


def run(catalog_pages_payload: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    for page in catalog_pages_payload.get("pages", []):
        html_text = Path(page["saved_path"]).read_text(encoding="utf-8")
        soup = make_soup(html_text)
        cards = soup.select(".products .wd-product")
        for position, card in enumerate(cards, start=1):
            link = card.select_one("a.product-image-link, h3 a, a")
            title_tag = card.select_one(".wd-entities-title, h2, h3")
            price_tag = card.select_one(".price ins .woocommerce-Price-amount, .price .woocommerce-Price-amount")
            old_price_tag = card.select_one(".price del .woocommerce-Price-amount")
            product_url = link.get("href") if link else None
            if not product_url:
                continue
            preview_images = clean_images([_pick_preview_image(card) or ""])
            items.append({
                "supplier_category_name": page["supplier_category_name"],
                "category_key": page["category_key"],
                "listing": {
                    "product_url": product_url,
                    "slug": slug_from_url(product_url),
                    "title_listing": normalize_spaces(title_tag.get_text(" ", strip=True) if title_tag else None),
                    "price_listing": parse_price_to_number(price_tag.get_text(" ", strip=True) if price_tag else None),
                    "old_price_listing": parse_price_to_number(old_price_tag.get_text(" ", strip=True) if old_price_tag else None),
                    "currency": "RUB",
                    "image_preview": preview_images[0] if preview_images else None,
                    "page_number": page["page_number"],
                    "position_on_page": position,
                },
            })

    return {
        "supplier_key": "demiand",
        "parsed_at": now_iso(),
        "items_count": len(items),
        "items": items,
    }
