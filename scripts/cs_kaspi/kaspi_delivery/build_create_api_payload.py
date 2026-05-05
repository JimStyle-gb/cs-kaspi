from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.time_utils import now_iso
from scripts.cs_kaspi.kaspi_delivery.common import (
    delivery_sku,
    int_or_zero,
    item_warning_flags,
    safe_dict,
    safe_list,
    text,
)


def _create_item(item: dict[str, Any]) -> dict[str, Any]:
    sku, sku_source = delivery_sku(item)
    attributes = safe_dict(item.get("kaspi_attributes"))
    images = safe_list(item.get("kaspi_images"))
    kaspi_category_code = text(item.get("kaspi_category_code")) or None

    live_blockers: list[str] = []
    if not kaspi_category_code:
        live_blockers.append("missing_kaspi_category_code")
    if item.get("kaspi_template_status") != "template_ready":
        live_blockers.append("kaspi_template_not_ready")
    live_blockers.append("kaspi_api_live_sender_not_enabled")
    warnings = item_warning_flags(item)

    return {
        "mode": "draft_only",
        "source_action": "create_candidate",
        "product_key": item.get("product_key"),
        "supplier_key": item.get("supplier_key"),
        "category_key": item.get("category_key"),
        "kaspi_category_code": kaspi_category_code,
        "kaspi_category_name": item.get("kaspi_category_name"),
        "kaspi_category_path": item.get("kaspi_category_path"),
        "kaspi_category_status": item.get("kaspi_category_status"),
        "kaspi_template_key": item.get("kaspi_template_key"),
        "kaspi_template_status": item.get("kaspi_template_status"),
        "kaspi_template_errors": item.get("kaspi_template_errors") or [],
        "kaspi_sku": sku,
        "sku_source": sku_source,
        "title": item.get("kaspi_title"),
        "brand": item.get("brand"),
        "description": item.get("kaspi_description"),
        "images": images,
        "attributes": attributes,
        "price_preview": int_or_zero(item.get("kaspi_price")),
        "stock_preview": int_or_zero(item.get("kaspi_stock")),
        "lead_time_days_preview": int_or_zero(item.get("lead_time_days")),
        "market": {
            "source": item.get("market_source"),
            "url": item.get("market_url"),
            "price": item.get("market_price"),
            "stock": item.get("market_stock"),
        },
        "official": {
            "article": item.get("official_article"),
            "url": item.get("official_url"),
            "title": item.get("official_title"),
        },
        "review": {
            "live_ready": False,
            "warnings": warnings,
            "live_blockers": live_blockers,
            "note": "Draft payload only. Before live API send, real Kaspi category codes/attributes and SKU allowlist must be approved.",
        },
    }


def run(create_candidates: list[dict[str, Any]], export_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    items = [_create_item(item) for item in create_candidates if isinstance(item, dict)]
    return {
        "meta": {
            "built_at": now_iso(),
            "mode": "draft_only",
            "source": "kaspi_create_candidates.json",
            "items": len(items),
            "export_built_at": safe_dict(export_meta).get("built_at"),
            "note": "These records are API-create drafts only. Nothing is sent to Kaspi.",
        },
        "items": items,
    }
