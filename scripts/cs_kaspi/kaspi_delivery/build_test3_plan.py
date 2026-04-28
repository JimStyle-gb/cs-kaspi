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
    valid_kaspi_sku,
)

REQUIRED_ACTIONS = ("create_candidate", "update_candidate", "pause_candidate")


def _first(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in rows:
        if isinstance(row, dict):
            return row
    return None


def _candidate_summary(item: dict[str, Any] | None, *, action: str) -> dict[str, Any] | None:
    if not item:
        return None

    sku, sku_source = delivery_sku(item)
    warnings = item_warning_flags(item)
    price = int_or_zero(item.get("kaspi_price"))
    stock = int_or_zero(item.get("kaspi_stock"))

    return {
        "source_action": action,
        "product_key": item.get("product_key"),
        "supplier_key": item.get("supplier_key"),
        "category_key": item.get("category_key"),
        "brand": item.get("brand"),
        "official_article": item.get("official_article"),
        "market_source": item.get("market_source"),
        "market_url": item.get("market_url"),
        "market_price": item.get("market_price"),
        "market_stock": item.get("market_stock"),
        "kaspi_match_exists": item.get("kaspi_match_exists"),
        "kaspi_product_id": item.get("kaspi_product_id"),
        "kaspi_sku": sku,
        "sku_source": sku_source,
        "kaspi_existing_title": item.get("kaspi_existing_title"),
        "kaspi_url": item.get("kaspi_url"),
        "kaspi_title": item.get("kaspi_title"),
        "kaspi_price": price if price > 0 else None,
        "kaspi_stock": stock,
        "lead_time_days": int_or_zero(item.get("lead_time_days")),
        "images_count": item.get("images_count"),
        "attributes_count": item.get("attributes_count"),
        "warnings": warnings,
    }


def _selected_candidates(
    *,
    create_candidates: list[dict[str, Any]],
    update_candidates: list[dict[str, Any]],
    pause_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "create_candidate": _candidate_summary(_first(create_candidates), action="create_candidate"),
        "update_candidate": _candidate_summary(_first(update_candidates), action="update_candidate"),
        "pause_candidate": _candidate_summary(_first(pause_candidates), action="pause_candidate"),
    }


def _candidate_blockers(action: str, item: dict[str, Any] | None) -> list[str]:
    if not item:
        return [f"missing_{action}"]

    blockers: list[str] = []
    sku = text(item.get("kaspi_sku"))
    sku_source = text(item.get("sku_source"))
    price = int_or_zero(item.get("kaspi_price"))
    stock = int_or_zero(item.get("kaspi_stock"))

    if not valid_kaspi_sku(sku):
        blockers.append(f"{action}_invalid_kaspi_sku")

    if action == "create_candidate":
        if not text(item.get("kaspi_title")):
            blockers.append("create_candidate_missing_title")
        if not text(item.get("brand")):
            blockers.append("create_candidate_missing_brand")
        if not text(item.get("category_key")):
            blockers.append("create_candidate_missing_category_key")
        if price <= 0:
            blockers.append("create_candidate_missing_price")
        if stock <= 0:
            blockers.append("create_candidate_missing_stock")
        blockers.append("create_candidate_needs_kaspi_category_and_attribute_mapping")
        blockers.append("kaspi_api_live_sender_not_enabled")

    if action == "update_candidate":
        if item.get("kaspi_match_exists") is not True:
            blockers.append("update_candidate_without_confirmed_kaspi_match")
        if sku_source != "existing_kaspi_sku":
            blockers.append("update_candidate_without_existing_kaspi_sku")
        if price <= 0:
            blockers.append("update_candidate_missing_price")
        if stock <= 0:
            blockers.append("update_candidate_missing_stock")
        blockers.append("xml_live_channel_not_enabled")

    if action == "pause_candidate":
        if item.get("kaspi_match_exists") is not True:
            blockers.append("pause_candidate_without_confirmed_kaspi_match")
        if sku_source != "existing_kaspi_sku":
            blockers.append("pause_candidate_without_existing_kaspi_sku")
        blockers.append("xml_live_channel_not_enabled")

    return blockers


def _readiness(selected: dict[str, Any]) -> dict[str, Any]:
    missing_actions = [action for action in REQUIRED_ACTIONS if not selected.get(action)]
    blockers: list[str] = []
    for action in REQUIRED_ACTIONS:
        blockers.extend(_candidate_blockers(action, selected.get(action)))

    unique_blockers = sorted(dict.fromkeys(blockers))
    return {
        "goal": "prepare_exactly_one_create_one_update_one_pause_for_later_controlled_live_test",
        "has_all_three_actions": not missing_actions,
        "missing_actions": missing_actions,
        "ready_for_human_review": not missing_actions,
        "ready_for_live_send": False,
        "live_send_allowed": False,
        "blockers": unique_blockers,
        "required_before_live_send": [
            "confirm real Ozon/WB/manual market data for create/update products",
            "add real Kaspi existing records for update/pause products in input/kaspi/existing/",
            "map Kaspi category codes and required Kaspi attributes for create products",
            "replace DRAFT_COMPANY/DRAFT_MERCHANT_ID/DRAFT_STORE_ID only after XML channel is approved",
            "add KASPI_ALLOWED_SKUS allowlist with exactly the 3 approved SKU",
            "keep KASPI_MAX_ACTIONS=3 for the first live test",
            "run dry-run preview before any live API/XML action",
        ],
    }


def _preview_text(plan: dict[str, Any]) -> str:
    lines: list[str] = []
    meta = safe_dict(plan.get("meta"))
    readiness = safe_dict(plan.get("readiness"))
    counts = safe_dict(plan.get("candidate_counts"))
    selected = safe_dict(plan.get("selected"))

    lines.append("CS-Kaspi controlled 3-product test plan")
    lines.append(f"built_at: {meta.get('built_at')}")
    lines.append("mode: draft_only")
    lines.append("nothing_sent_to_kaspi: true")
    lines.append("")
    lines.append("candidate_counts:")
    for action in REQUIRED_ACTIONS:
        lines.append(f"  {action}: {counts.get(action, 0)}")
    lines.append("")
    lines.append("readiness:")
    lines.append(f"  has_all_three_actions: {readiness.get('has_all_three_actions')}")
    lines.append(f"  ready_for_human_review: {readiness.get('ready_for_human_review')}")
    lines.append(f"  ready_for_live_send: {readiness.get('ready_for_live_send')}")
    lines.append(f"  live_send_allowed: {readiness.get('live_send_allowed')}")
    lines.append("")
    lines.append("missing_actions:")
    missing = safe_list(readiness.get("missing_actions"))
    if missing:
        for item in missing:
            lines.append(f"  - {item}")
    else:
        lines.append("  none")
    lines.append("")
    lines.append("blockers:")
    blockers = safe_list(readiness.get("blockers"))
    if blockers:
        for item in blockers:
            lines.append(f"  - {item}")
    else:
        lines.append("  none")
    lines.append("")

    for action in REQUIRED_ACTIONS:
        item = selected.get(action)
        lines.append(f"selected_{action}:")
        if not isinstance(item, dict):
            lines.append("  none")
            lines.append("")
            continue
        lines.append(f"  product_key: {item.get('product_key')}")
        lines.append(f"  kaspi_sku: {item.get('kaspi_sku')} ({item.get('sku_source')})")
        lines.append(f"  price: {item.get('kaspi_price')}")
        lines.append(f"  stock: {item.get('kaspi_stock')}")
        lines.append(f"  title: {item.get('kaspi_title')}")
        lines.append("")

    lines.append("required_before_live_send:")
    for item in safe_list(readiness.get("required_before_live_send")):
        lines.append(f"  - {item}")
    return "\n".join(lines) + "\n"


def run(
    *,
    create_candidates: list[dict[str, Any]],
    update_candidates: list[dict[str, Any]],
    pause_candidates: list[dict[str, Any]],
    delivery_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected = _selected_candidates(
        create_candidates=create_candidates,
        update_candidates=update_candidates,
        pause_candidates=pause_candidates,
    )
    candidate_counts = {
        "create_candidate": len(create_candidates),
        "update_candidate": len(update_candidates),
        "pause_candidate": len(pause_candidates),
    }
    plan = {
        "meta": {
            "built_at": now_iso(),
            "mode": "draft_only",
            "nothing_sent_to_kaspi": True,
            "source": "kaspi export candidates",
            "delivery_mode": safe_dict(delivery_summary).get("mode"),
            "note": "This is a controlled 3-product test plan. It never sends anything to Kaspi.",
        },
        "candidate_counts": candidate_counts,
        "selected": selected,
        "readiness": _readiness(selected),
    }
    plan["preview_text"] = _preview_text(plan)
    return plan
