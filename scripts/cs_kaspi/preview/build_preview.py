from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.time_utils import now_iso


def _item(product: dict[str, Any]) -> dict[str, Any]:
    official = product.get("official", {}) or {}
    kaspi = product.get("kaspi_policy", {}) or {}
    status = product.get("status", {}) or {}
    attrs = kaspi.get("kaspi_attributes", {}) or {}
    images = kaspi.get("kaspi_images", []) or []
    return {
        "product_key": product.get("product_key"),
        "supplier_key": product.get("supplier_key"),
        "category_key": product.get("category_key"),
        "supplier_category_name": product.get("supplier_category_name"),
        "brand": product.get("brand"),
        "model_key": product.get("model_key"),
        "variant_key": product.get("variant_key"),
        "official_url": official.get("url"),
        "official_title": official.get("title_official"),
        "official_article": official.get("product_id"),
        "official_price": official.get("price"),
        "official_old_price": official.get("old_price"),
        "official_available": official.get("available"),
        "kaspi_title": kaspi.get("kaspi_title"),
        "kaspi_price": kaspi.get("kaspi_price"),
        "kaspi_stock": kaspi.get("kaspi_stock"),
        "lead_time_days": kaspi.get("lead_time_days"),
        "kaspi_available": kaspi.get("kaspi_available"),
        "images_count": len(images),
        "first_image": images[0] if images else None,
        "attributes_count": len(attrs),
        "description_length": len(kaspi.get("kaspi_description") or ""),
        "lifecycle_status": status.get("lifecycle_status"),
        "action_status": status.get("action_status"),
        "needs_review": status.get("needs_review"),
        "review_reasons": status.get("review_reasons", []),
    }


def run(master_catalog: dict[str, Any]) -> dict[str, Any]:
    products = [_item(p) for p in master_catalog.get("products", [])]
    return {
        "meta": {
            "built_at": now_iso(),
            "total_products": len(products),
        },
        "products": products,
    }
