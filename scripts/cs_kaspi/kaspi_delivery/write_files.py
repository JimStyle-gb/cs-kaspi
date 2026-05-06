from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.json_io import write_json
from scripts.cs_kaspi.kaspi_delivery.common import rel, safe_dict, safe_list


def _preview_text(summary: dict[str, Any], create_payload: dict[str, Any], price_stock: dict[str, Any]) -> str:
    create_items = safe_list(create_payload.get("items"))
    update_plan = safe_list(price_stock.get("update_plan"))
    pause_plan = safe_list(price_stock.get("pause_plan"))

    lines: list[str] = []
    lines.append("CS-Kaspi Kaspi delivery draft")
    lines.append(f"built_at: {summary.get('built_at')}")
    lines.append("mode: draft_only")
    lines.append("live_send_enabled: false")
    lines.append("note: nothing is sent to Kaspi API; files are for review only")
    lines.append("")
    lines.append(f"total_products: {summary.get('total_products')}")
    lines.append(f"ready_products: {summary.get('ready_products')}")
    lines.append(f"create_api_draft_items: {summary.get('create_api_draft_items')}")
    lines.append(f"price_stock_xml_items: {summary.get('price_stock_xml_items')}")
    lines.append(f"update_xml_items: {summary.get('update_xml_items')}")
    lines.append(f"pause_xml_items: {summary.get('pause_xml_items')}")
    lines.append("")
    lines.append("warning_counts:")
    warning_counts = safe_dict(summary.get("warning_counts"))
    if warning_counts:
        for key, value in warning_counts.items():
            lines.append(f"  {key}: {value}")
    else:
        lines.append("  none")
    lines.append("")

    def add_section(title: str, rows: list[dict[str, Any]], *, title_key: str = "title", limit: int = 30) -> None:
        lines.append(title)
        if not rows:
            lines.append("  none")
            lines.append("")
            return
        for index, row in enumerate(rows[:limit], start=1):
            lines.append(
                "  "
                + f"{index}. {row.get('product_key')} | sku={row.get('kaspi_sku')} | "
                + f"price={row.get('price') or row.get('price_preview')} | "
                + f"stock={row.get('stock') or row.get('stock_preview')} | "
                + f"category={row.get('kaspi_category_code') or '-'}:{row.get('kaspi_category_name') or '-'} | "
                + str(row.get(title_key) or "")
            )
        if len(rows) > limit:
            lines.append(f"  ... and {len(rows) - limit} more")
        lines.append("")

    add_section("create_api_payload:", create_items)
    add_section("xml_update_plan:", update_plan)
    add_section("xml_pause_plan:", pause_plan)

    lines.append("safety:")
    for key, value in safe_dict(summary.get("safety")).items():
        lines.append(f"  {key}: {value}")
    return "\n".join(lines) + "\n"


def run(
    out_dir: Path,
    *,
    create_payload: dict[str, Any],
    price_stock: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "create_api_payload_json": out_dir / "kaspi_create_api_payload.json",
        "price_stock_xml": out_dir / "kaspi_price_stock.xml",
        "update_plan_json": out_dir / "kaspi_update_plan.json",
        "pause_plan_json": out_dir / "kaspi_pause_plan.json",
        "delivery_summary_json": out_dir / "kaspi_delivery_summary.json",
        "delivery_preview_txt": out_dir / "kaspi_delivery_preview.txt",
    }

    write_json(paths["create_api_payload_json"], create_payload)
    paths["price_stock_xml"].write_text(str(price_stock.get("xml") or ""), encoding="utf-8")
    write_json(
        paths["update_plan_json"],
        {"meta": safe_dict(price_stock.get("meta")), "products": safe_list(price_stock.get("update_plan"))},
    )
    write_json(
        paths["pause_plan_json"],
        {"meta": safe_dict(price_stock.get("meta")), "products": safe_list(price_stock.get("pause_plan"))},
    )
    write_json(paths["delivery_summary_json"], summary)
    paths["delivery_preview_txt"].write_text(_preview_text(summary, create_payload, price_stock), encoding="utf-8")

    return {key: rel(path) for key, path in paths.items()}
