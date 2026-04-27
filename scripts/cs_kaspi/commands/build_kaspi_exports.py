from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.json_io import read_json, write_json
from scripts.cs_kaspi.core.paths import ROOT, path_from_config
from scripts.cs_kaspi.core.time_utils import now_iso

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
    "official_title",
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


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except Exception:
        return path.as_posix()


def _export_item(product: dict[str, Any], *, action: str) -> dict[str, Any]:
    official = _safe_dict(product.get("official"))
    market = _safe_dict(product.get("market"))
    kaspi = _safe_dict(product.get("kaspi_policy"))
    status = _safe_dict(product.get("status"))
    match = _safe_dict(product.get("kaspi_match"))
    attrs = _safe_dict(kaspi.get("kaspi_attributes"))
    images = _safe_list(kaspi.get("kaspi_images"))

    return {
        "export_mode": "draft_only",
        "export_action": action,
        "product_key": product.get("product_key"),
        "supplier_key": product.get("supplier_key"),
        "category_key": product.get("category_key"),
        "supplier_category_name": product.get("supplier_category_name"),
        "brand": product.get("brand"),
        "model_key": product.get("model_key"),
        "variant_key": product.get("variant_key"),
        "official_article": official.get("product_id"),
        "official_url": official.get("url"),
        "official_title": official.get("title_official"),
        "market_sellable": market.get("sellable"),
        "market_source": market.get("market_price_source"),
        "market_url": market.get("market_url"),
        "market_price": market.get("market_price"),
        "market_stock": market.get("stock"),
        "kaspi_product_id": match.get("kaspi_product_id"),
        "kaspi_sku": product.get("product_key"),
        "kaspi_title": kaspi.get("kaspi_title"),
        "kaspi_price": kaspi.get("kaspi_price"),
        "kaspi_stock": kaspi.get("kaspi_stock"),
        "lead_time_days": kaspi.get("lead_time_days"),
        "kaspi_available": kaspi.get("kaspi_available"),
        "kaspi_images": images,
        "kaspi_description": kaspi.get("kaspi_description"),
        "kaspi_attributes": attrs,
        "images_count": len(images),
        "attributes_count": len(attrs),
        "lifecycle_status": status.get("lifecycle_status"),
        "action_status": status.get("action_status"),
        "needs_review": bool(status.get("needs_review")),
        "review_reasons": status.get("review_reasons") or [],
    }


def _build_plan(master_catalog: dict[str, Any]) -> dict[str, Any]:
    products = [p for p in master_catalog.get("products", []) if isinstance(p, dict)]
    create_candidates: list[dict[str, Any]] = []
    update_candidates: list[dict[str, Any]] = []
    pause_candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for product in products:
        kaspi = _safe_dict(product.get("kaspi_policy"))
        status = _safe_dict(product.get("status"))
        match = _safe_dict(product.get("kaspi_match"))

        ready = status.get("action_status") == "ready_for_create_or_update"
        available = kaspi.get("kaspi_available") is True
        matched = match.get("exists") is True

        if ready and available and matched:
            update_candidates.append(_export_item(product, action="update_candidate"))
        elif ready and available:
            create_candidates.append(_export_item(product, action="create_candidate"))
        elif matched and not available:
            pause_candidates.append(_export_item(product, action="pause_candidate"))
        else:
            skipped.append(_export_item(product, action="skipped"))

    ready_products = create_candidates + update_candidates
    meta = {
        "built_at": now_iso(),
        "export_mode": "draft_only",
        "total_products": len(products),
        "ready_products": len(ready_products),
        "create_candidates": len(create_candidates),
        "update_candidates": len(update_candidates),
        "pause_candidates": len(pause_candidates),
        "skipped": len(skipped),
        "note": "Draft files only. Nothing is sent to Kaspi API.",
    }

    return {
        "meta": meta,
        "ready_products": ready_products,
        "create_candidates": create_candidates,
        "update_candidates": update_candidates,
        "pause_candidates": pause_candidates,
        "skipped": skipped,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_HEADERS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _text(row.get(key)) for key in CSV_HEADERS})


def _write_txt(path: Path, plan: dict[str, Any]) -> None:
    meta = _safe_dict(plan.get("meta"))
    create_candidates = _safe_list(plan.get("create_candidates"))
    update_candidates = _safe_list(plan.get("update_candidates"))
    pause_candidates = _safe_list(plan.get("pause_candidates"))
    skipped = _safe_list(plan.get("skipped"))

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
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_files(plan: dict[str, Any]) -> dict[str, str]:
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

    meta = _safe_dict(plan.get("meta"))
    ready_products = _safe_list(plan.get("ready_products"))
    create_candidates = _safe_list(plan.get("create_candidates"))
    update_candidates = _safe_list(plan.get("update_candidates"))
    pause_candidates = _safe_list(plan.get("pause_candidates"))
    skipped = _safe_list(plan.get("skipped"))

    write_json(paths["summary_json"], meta)
    write_json(paths["ready_json"], {"meta": meta, "products": ready_products})
    write_json(paths["create_json"], {"meta": meta, "products": create_candidates})
    write_json(paths["update_json"], {"meta": meta, "products": update_candidates})
    write_json(paths["pause_json"], {"meta": meta, "products": pause_candidates})
    write_json(paths["skipped_json"], {"meta": meta, "products": skipped})
    _write_csv(paths["preview_csv"], ready_products)
    _write_txt(paths["preview_txt"], plan)

    return {key: _rel(path) for key, path in paths.items()}


def _validate_plan(plan: dict[str, Any]) -> None:
    meta = _safe_dict(plan.get("meta"))
    total = int(meta.get("total_products") or 0)
    ready = int(meta.get("ready_products") or 0)
    create = int(meta.get("create_candidates") or 0)
    update = int(meta.get("update_candidates") or 0)
    pause = int(meta.get("pause_candidates") or 0)
    skipped = int(meta.get("skipped") or 0)

    if total <= 0:
        raise RuntimeError("Kaspi export plan is empty: total_products=0")
    if ready != create + update:
        raise RuntimeError("Kaspi export plan counters are inconsistent: ready != create + update")
    if total != create + update + pause + skipped:
        raise RuntimeError("Kaspi export plan counters are inconsistent: total != create + update + pause + skipped")


def run() -> dict[str, Any]:
    state_dir = path_from_config("artifacts_state_dir")
    catalog = read_json(state_dir / "master_catalog.json", required=True)
    if not isinstance(catalog, dict):
        raise RuntimeError("master_catalog.json must be a JSON object")
    products = catalog.get("products", [])
    if not products:
        raise RuntimeError("master_catalog.json has no products. Run build_master_catalog first.")

    plan = _build_plan(catalog)
    _validate_plan(plan)
    files = _write_files(plan)
    return {"meta": plan.get("meta", {}), "files": files}


if __name__ == "__main__":
    run()
