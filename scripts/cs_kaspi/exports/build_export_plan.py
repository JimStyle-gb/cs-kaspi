from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.json_io import write_json
from scripts.cs_kaspi.core.paths import ROOT, path_from_config

CSV_HEADERS = [
    "export_action",
    "product_key",
    "supplier_key",
    "category_key",
    "brand",
    "model_key",
    "variant_key",
    "official_article",
    "official_url",
    "market_source",
    "market_url",
    "market_price",
    "market_stock",
    "kaspi_sku",
    "kaspi_product_id",
    "kaspi_title",
    "kaspi_price",
    "kaspi_stock",
    "lead_time_days",
    "kaspi_available",
    "images_count",
    "attributes_count",
    "lifecycle_status",
    "action_status",
    "needs_review",
]


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except Exception:
        return path.as_posix()


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_HEADERS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _text(row.get(key)) for key in CSV_HEADERS})


def _write_txt(path: Path, plan: dict[str, Any]) -> None:
    meta = plan.get("meta", {}) or {}
    create_candidates = plan.get("create_candidates", []) or []
    update_candidates = plan.get("update_candidates", []) or []
    pause_candidates = plan.get("pause_candidates", []) or []
    skipped = plan.get("skipped", []) or []

    lines: list[str] = []
    lines.append("CS-Kaspi export draft")
    lines.append(f"built_at: {meta.get('built_at')}")
    lines.append("mode: draft_only")
    lines.append("note: files are for review only; nothing is sent to Kaspi API")
    lines.append("")
    lines.append(f"total_products: {meta.get('total_products')}")
    lines.append(f"ready_products: {meta.get('ready_products')}")
    lines.append(f"create_candidates: {meta.get('create_candidates')}")
    lines.append(f"update_candidates: {meta.get('update_candidates')}")
    lines.append(f"pause_candidates: {meta.get('pause_candidates')}")
    lines.append(f"skipped: {meta.get('skipped')}")
    lines.append("")

    def add_section(title: str, rows: list[dict[str, Any]], limit: int = 30) -> None:
        lines.append(title)
        if not rows:
            lines.append("  none")
            lines.append("")
            return
        for idx, row in enumerate(rows[:limit], start=1):
            lines.append(
                "  "
                + f"{idx}. {row.get('product_key')} | "
                + f"{row.get('kaspi_price')} KZT | stock={row.get('kaspi_stock')} | "
                + str(row.get("kaspi_title") or "")
            )
        if len(rows) > limit:
            lines.append(f"  ... and {len(rows) - limit} more")
        lines.append("")

    add_section("create_candidates:", create_candidates)
    add_section("update_candidates:", update_candidates)
    add_section("pause_candidates:", pause_candidates)
    add_section("skipped:", skipped, limit=15)
    path.write_text("\n".join(lines), encoding="utf-8")


def run(plan: dict[str, Any]) -> dict[str, str]:
    out_dir = path_from_config("artifacts_exports_dir")
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "summary_json": out_dir / "kaspi_export_summary.json",
        "ready_json": out_dir / "kaspi_ready_products.json",
        "create_json": out_dir / "kaspi_create_candidates.json",
        "update_json": out_dir / "kaspi_update_candidates.json",
        "pause_json": out_dir / "kaspi_pause_candidates.json",
        "skipped_json": out_dir / "kaspi_skipped_products.json",
        "preview_csv": out_dir / "kaspi_export_preview.csv",
        "preview_txt": out_dir / "kaspi_export_preview.txt",
    }

    write_json(paths["summary_json"], plan.get("meta", {}) or {})
    write_json(paths["ready_json"], {"meta": plan.get("meta", {}), "products": plan.get("ready_products", [])})
    write_json(paths["create_json"], {"meta": plan.get("meta", {}), "products": plan.get("create_candidates", [])})
    write_json(paths["update_json"], {"meta": plan.get("meta", {}), "products": plan.get("update_candidates", [])})
    write_json(paths["pause_json"], {"meta": plan.get("meta", {}), "products": plan.get("pause_candidates", [])})
    write_json(paths["skipped_json"], {"meta": plan.get("meta", {}), "products": plan.get("skipped", [])})
    _write_csv(paths["preview_csv"], plan.get("ready_products", []) or [])
    _write_txt(paths["preview_txt"], plan)

    return {key: _rel(path) for key, path in paths.items()}
