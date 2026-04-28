from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.json_io import write_json
from scripts.cs_kaspi.core.paths import ROOT, ensure_runtime_dirs, path_from_config
from scripts.cs_kaspi.core.time_utils import now_iso

SOURCE_DIR = ROOT / "input" / "market" / "worklists"
GENERATED_PATH = ROOT / "input" / "market" / "manual" / "_generated_from_worklists.csv"

OUTPUT_HEADERS = [
    "source",
    "product_key",
    "supplier_key",
    "category_key",
    "model_key",
    "variant_key",
    "official_article",
    "title",
    "url",
    "price",
    "available",
    "stock",
    "lead_time_days",
    "rating",
    "reviews_count",
]

_IGNORED_NAME_PARTS = ("readme", "example", "sample")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def _first(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _text(row.get(key))
        if value:
            return value
    return ""


def _is_filled_market_row(row: dict[str, Any]) -> bool:
    if not _first(row, "product_key", "cs_product_key"):
        return False
    filled_values = [
        _first(row, "fill_url", "url", "market_url", "product_url"),
        _first(row, "fill_price", "price", "market_price", "current_price"),
        _first(row, "fill_available", "available", "in_stock"),
        _first(row, "fill_stock", "stock", "quantity", "qty"),
    ]
    return any(filled_values)


def _source(row: dict[str, Any]) -> str:
    source = _first(row, "fill_source", "source", "market_source", "recommended_source")
    source = source.lower()
    if source in {"wildberries", "wb"}:
        return "wb"
    if source == "ozon":
        return "ozon"
    return "manual"


def _available(row: dict[str, Any]) -> str:
    value = _first(row, "fill_available", "available", "in_stock")
    if value:
        return value
    stock = _first(row, "fill_stock", "stock", "quantity", "qty")
    try:
        if int(float(stock.replace(" ", "").replace(",", "."))) > 0:
            return "true"
    except Exception:
        pass
    return ""


def _lead_time(row: dict[str, Any]) -> str:
    return _first(row, "fill_lead_time_days", "lead_time_days", "delivery_days", "lead_time") or "20"


def _output_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        "source": _source(row),
        "product_key": _first(row, "product_key", "cs_product_key"),
        "supplier_key": _first(row, "supplier_key", "supplier"),
        "category_key": _first(row, "category_key", "category"),
        "model_key": _first(row, "model_key", "model"),
        "variant_key": _first(row, "variant_key", "variant", "color_key"),
        "official_article": _first(row, "official_article", "article", "sku", "vendor_code", "product_id"),
        "title": _first(row, "title", "official_title", "kaspi_title", "market_title", "product_name"),
        "url": _first(row, "fill_url", "url", "market_url", "product_url"),
        "price": _first(row, "fill_price", "price", "market_price", "current_price"),
        "available": _available(row),
        "stock": _first(row, "fill_stock", "stock", "quantity", "qty"),
        "lead_time_days": _lead_time(row),
        "rating": _first(row, "rating", "stars"),
        "reviews_count": _first(row, "reviews_count", "reviews", "feedbacks"),
    }


def _iter_source_files() -> list[Path]:
    if not SOURCE_DIR.exists():
        return []
    files: list[Path] = []
    for path in SOURCE_DIR.rglob("*.csv"):
        if not path.is_file():
            continue
        name = path.name.lower()
        if any(part in name for part in _IGNORED_NAME_PARTS):
            continue
        files.append(path)
    return sorted(files)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _write_generated(rows: list[dict[str, str]]) -> None:
    GENERATED_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        if GENERATED_PATH.exists():
            GENERATED_PATH.unlink()
        return

    with GENERATED_PATH.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_HEADERS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _text(row.get(key)) for key in OUTPUT_HEADERS})


def _txt_report(report: dict[str, Any]) -> str:
    lines = [
        "CS-Kaspi market worklist import",
        f"checked_at: {report.get('checked_at')}",
        f"source_dir: {report.get('source_dir')}",
        f"source_files: {report.get('source_files')}",
        f"source_rows: {report.get('source_rows')}",
        f"imported_rows: {report.get('imported_rows')}",
        f"generated_file: {report.get('generated_file') or ''}",
        "",
        "files:",
    ]
    for item in report.get("files_detail", []):
        lines.append(f"  {item.get('file')} | rows={item.get('rows')} | imported={item.get('imported')}")
    lines.extend(["", "problems:"])
    for item in report.get("problems", []):
        lines.append(f"  [{item.get('level')}] {item.get('message')} | file={item.get('file')} | row={item.get('row')}")
    return "\n".join(lines) + "\n"


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except Exception:
        return path.as_posix()


def run() -> dict[str, Any]:
    ensure_runtime_dirs()
    reports_dir = path_from_config("artifacts_reports_dir")
    files = _iter_source_files()

    imported: list[dict[str, str]] = []
    files_detail: list[dict[str, Any]] = []
    problems: list[dict[str, Any]] = []
    source_rows = 0

    for path in files:
        try:
            rows = _read_csv(path)
        except Exception as exc:
            problems.append({"level": "critical", "message": f"cannot read worklist csv: {exc}", "file": _rel(path)})
            continue

        file_imported = 0
        source_rows += len(rows)
        for index, row in enumerate(rows, start=2):
            if not _is_filled_market_row(row):
                continue
            out = _output_row(row)
            if not out.get("product_key"):
                problems.append({"level": "critical", "message": "filled market row has empty product_key", "file": _rel(path), "row": index})
                continue
            imported.append(out)
            file_imported += 1

        files_detail.append({"file": _rel(path), "rows": len(rows), "imported": file_imported})

    _write_generated(imported)

    report = {
        "checked_at": now_iso(),
        "source_dir": _rel(SOURCE_DIR),
        "source_files": len(files),
        "source_rows": source_rows,
        "imported_rows": len(imported),
        "generated_file": _rel(GENERATED_PATH) if imported else "",
        "files_detail": files_detail,
        "critical_count": sum(1 for item in problems if item.get("level") == "critical"),
        "problems": problems,
        "note": "Put filled worklist CSV files into input/market/worklists/. They will be converted into a temporary standard market input before refresh_market_data.",
    }

    write_json(reports_dir / "market_worklist_import_report.json", report)
    (reports_dir / "market_worklist_import_report.txt").write_text(_txt_report(report), encoding="utf-8")

    if report["critical_count"]:
        raise RuntimeError(f"Market worklist import failed: {report['critical_count']} critical issue(s). See artifacts/reports/market_worklist_import_report.txt")

    return report


if __name__ == "__main__":
    run()
