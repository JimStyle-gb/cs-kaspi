from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.time_utils import now_iso
from scripts.cs_kaspi.kaspi_delivery.common import delivery_config, safe_dict, safe_list, text


def _count_warnings(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        review = safe_dict(item.get("review"))
        warnings = safe_list(review.get("warnings")) + safe_list(review.get("live_blockers")) + safe_list(item.get("warnings"))
        for warning in warnings:
            key = str(warning)
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def run(
    *,
    export_meta: dict[str, Any],
    create_payload: dict[str, Any],
    price_stock: dict[str, Any],
) -> dict[str, Any]:
    cfg = delivery_config()
    create_items = safe_list(create_payload.get("items"))
    update_plan = safe_list(price_stock.get("update_plan"))
    pause_plan = safe_list(price_stock.get("pause_plan"))
    xml_meta = safe_dict(price_stock.get("meta"))

    all_review_items = create_items + update_plan + pause_plan
    live_send_enabled = cfg.get("live_send_enabled") is True
    draft_company = text(cfg.get("company")) in {"", "DRAFT_COMPANY"}
    draft_merchant = text(cfg.get("merchant_id")) in {"", "DRAFT_MERCHANT_ID"}
    draft_store = text(cfg.get("store_id")) in {"", "DRAFT_STORE_ID"}

    return {
        "built_at": now_iso(),
        "mode": text(cfg.get("mode")) or "draft_only",
        "live_send_enabled": live_send_enabled,
        "source_export_built_at": safe_dict(export_meta).get("built_at"),
        "total_products": safe_dict(export_meta).get("total_products"),
        "ready_products": safe_dict(export_meta).get("ready_products"),
        "create_api_draft_items": len(create_items),
        "price_stock_xml_items": int(xml_meta.get("xml_items") or 0),
        "update_xml_items": len(update_plan),
        "pause_xml_items": len(pause_plan),
        "warning_counts": _count_warnings(all_review_items),
        "files_note": {
            "kaspi_create_api_payload.json": "draft payload for future API create flow",
            "kaspi_price_stock.xml": "draft XML for future price/stock/pause flow",
            "kaspi_update_plan.json": "items planned for XML update",
            "kaspi_pause_plan.json": "items planned for XML pause",
            "kaspi_delivery_preview.txt": "human-readable review before any live action",
        },
        "safety": {
            "nothing_sent_to_kaspi": True,
            "api_live_sender_present": False,
            "xml_live_channel_present": False,
            "xml_has_draft_values": draft_company or draft_merchant or draft_store,
            "max_actions_first_live_test": cfg.get("max_actions_first_live_test", 3),
            "allowed_skus_count": len(safe_list(cfg.get("allowed_skus"))),
            "recommended_next_live_guards": [
                "KASPI_LIVE_SEND=true only manually",
                "KASPI_ALLOWED_SKUS allowlist",
                "KASPI_MAX_ACTIONS limit",
                "manual approve file before send",
            ],
        },
    }
