from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from scripts.cs_kaspi.core.time_utils import now_iso
from scripts.cs_kaspi.kaspi_delivery.common import (
    delivery_config,
    delivery_sku,
    delivery_value,
    int_or_zero,
    item_warning_flags,
    text,
)


def _xml_offer(item: dict[str, Any], *, action: str, store_id: str) -> tuple[ET.Element, dict[str, Any]]:
    sku, sku_source = delivery_sku(item)
    available = "no" if action == "pause_candidate" else "yes"
    stock = 0 if action == "pause_candidate" else int_or_zero(item.get("kaspi_stock"))
    price = int_or_zero(item.get("kaspi_price"))
    lead_time_days = int_or_zero(item.get("lead_time_days"))

    offer = ET.Element("offer", {"sku": sku})
    ET.SubElement(offer, "model").text = text(item.get("kaspi_title")) or text(item.get("official_title"))
    ET.SubElement(offer, "brand").text = text(item.get("brand"))

    availabilities = ET.SubElement(offer, "availabilities")
    ET.SubElement(
        availabilities,
        "availability",
        {
            "available": available,
            "storeId": store_id,
            "preOrder": str(lead_time_days),
            "stockCount": str(stock),
        },
    )

    if price > 0:
        ET.SubElement(offer, "price").text = str(price)

    warnings = item_warning_flags(item)
    if action == "update_candidate" and price <= 0:
        warnings.append("update_candidate_without_price")
    if item.get("kaspi_match_exists") is not True:
        warnings.append("xml_item_without_confirmed_kaspi_match")
    if sku_source != "existing_kaspi_sku":
        warnings.append("xml_item_uses_generated_sku_not_existing_kaspi_sku")

    plan_item = {
        "source_action": action,
        "product_key": item.get("product_key"),
        "kaspi_sku": sku,
        "sku_source": sku_source,
        "available": available,
        "stock": stock,
        "price": price if price > 0 else None,
        "lead_time_days": lead_time_days,
        "brand": item.get("brand"),
        "title": item.get("kaspi_title"),
        "market_source": item.get("market_source"),
        "market_url": item.get("market_url"),
        "warnings": warnings,
    }
    return offer, plan_item


def _build_xml(
    offer_elements: list[ET.Element],
    *,
    built_at: str,
    company: str,
    merchant_id: str,
) -> str:
    root = ET.Element(
        "kaspi_catalog",
        {
            "date": built_at,
            "xmlns": "kaspiShopping",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "kaspiShopping http://kaspi.kz/kaspishopping.xsd",
        },
    )
    ET.SubElement(root, "company").text = company
    ET.SubElement(root, "merchantid").text = merchant_id
    offers = ET.SubElement(root, "offers")
    for offer in offer_elements:
        offers.append(offer)

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def run(update_candidates: list[dict[str, Any]], pause_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    built_at = now_iso()
    cfg = delivery_config()
    company = delivery_value(cfg, "company", "DRAFT_COMPANY")
    merchant_id = delivery_value(cfg, "merchant_id", "DRAFT_MERCHANT_ID")
    store_id = delivery_value(cfg, "store_id", "DRAFT_STORE_ID")

    offer_elements: list[ET.Element] = []
    update_plan: list[dict[str, Any]] = []
    pause_plan: list[dict[str, Any]] = []

    for item in update_candidates:
        if not isinstance(item, dict):
            continue
        if item.get("kaspi_template_status") != "template_ready":
            # Защита от старых/ручных файлов: update XML не должен обновлять товары,
            # которые не прошли обязательные поля Kaspi-шаблона.
            continue
        offer, plan_item = _xml_offer(item, action="update_candidate", store_id=store_id)
        offer_elements.append(offer)
        update_plan.append(plan_item)

    for item in pause_candidates:
        if not isinstance(item, dict):
            continue
        offer, plan_item = _xml_offer(item, action="pause_candidate", store_id=store_id)
        offer_elements.append(offer)
        pause_plan.append(plan_item)

    plan_items = update_plan + pause_plan
    return {
        "meta": {
            "built_at": built_at,
            "mode": text(cfg.get("mode")) or "draft_only",
            "live_send_enabled": cfg.get("live_send_enabled") is True,
            "xml_items": len(plan_items),
            "update_items": len(update_plan),
            "pause_items": len(pause_plan),
            "company": company,
            "merchantid": merchant_id,
            "store_id": store_id,
            "note": "Price/stock XML draft only. Live XML channel is disabled until manual approval.",
        },
        "xml": _build_xml(offer_elements, built_at=built_at, company=company, merchant_id=merchant_id),
        "update_plan": update_plan,
        "pause_plan": pause_plan,
    }
