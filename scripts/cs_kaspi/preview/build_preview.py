from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.time_utils import now_iso
from scripts.cs_kaspi.kaspi_templates.build_template_rows import build_row
from scripts.cs_kaspi.kaspi_templates.validate_rows import validate_row


def _item(product: dict[str, Any]) -> dict[str, Any]:
    official = product.get("official", {}) or {}
    market = product.get("market", {}) or {}
    kaspi = product.get("kaspi_policy", {}) or {}
    status = product.get("status", {}) or {}
    match = product.get("kaspi_match", {}) or {}
    attrs = kaspi.get("kaspi_attributes", {}) or {}
    images = kaspi.get("kaspi_images", []) or []
    template_key = ""
    template_status = "not_checked"
    template_errors: list[str] = []
    template_warnings: list[str] = []
    try:
        built_template = build_row(product)
        template_key = built_template.get("template_key") or ""
        template_errors.extend(built_template.get("errors") or [])
        template = built_template.get("template") or {}
        row = built_template.get("row") or {}
        if row and template:
            validation = validate_row(row, template)
            template_errors.extend(validation.get("errors") or [])
            template_warnings.extend(validation.get("warnings") or [])
        template_status = "template_ready" if not template_errors else "template_blocked"
    except Exception as exc:
        template_status = "template_check_failed"
        template_errors = [str(exc)]

    return {
        "product_key": product.get("product_key"),
        "supplier_key": product.get("supplier_key"),
        "category_key": product.get("category_key"),
        "supplier_category_name": product.get("supplier_category_name"),
        "kaspi_category_code": kaspi.get("kaspi_category_code"),
        "kaspi_category_name": kaspi.get("kaspi_category_name"),
        "kaspi_category_path": kaspi.get("kaspi_category_path"),
        "kaspi_category_status": kaspi.get("kaspi_category_status"),
        "brand": product.get("brand"),
        "model_key": product.get("model_key"),
        "variant_key": product.get("variant_key"),
        "official_url": official.get("url"),
        "official_title": official.get("title_official"),
        "official_article": official.get("product_id"),
        "official_price": official.get("price"),
        "official_old_price": official.get("old_price"),
        "official_available": official.get("available"),
        "market_sellable": market.get("sellable"),
        "market_sellable_reason": market.get("sellable_reason"),
        "market_price": market.get("market_price"),
        "market_price_source": market.get("market_price_source"),
        "market_url": market.get("market_url"),
        "market_stock": market.get("stock"),
        "market_lead_time_days": market.get("lead_time_days"),
        "market_sources_count": len(market.get("sources", {}) or {}),
        "kaspi_title": kaspi.get("kaspi_title"),
        "kaspi_price": kaspi.get("kaspi_price"),
        "kaspi_stock": kaspi.get("kaspi_stock"),
        "lead_time_days": kaspi.get("lead_time_days"),
        "kaspi_available": kaspi.get("kaspi_available"),
        "price_source": kaspi.get("price_source"),
        "kaspi_template_key": template_key,
        "kaspi_template_status": template_status,
        "kaspi_template_errors": template_errors,
        "kaspi_template_warnings": template_warnings,
        "kaspi_match_exists": match.get("exists"),
        "kaspi_product_id": match.get("kaspi_product_id"),
        "kaspi_sku": match.get("kaspi_sku"),
        "kaspi_existing_title": match.get("kaspi_title"),
        "kaspi_existing_url": match.get("kaspi_url"),
        "kaspi_matched_by": match.get("matched_by"),
        "kaspi_match_confidence": match.get("confidence"),
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
