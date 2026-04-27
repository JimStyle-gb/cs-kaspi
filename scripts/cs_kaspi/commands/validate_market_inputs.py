from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.json_io import read_json, write_json
from scripts.cs_kaspi.core.paths import ensure_runtime_dirs, path_from_config
from scripts.cs_kaspi.core.time_utils import now_iso


_REQUIRED_SELLABLE_FIELDS = ("market_price", "market_price_source", "stock")
_URL_REQUIRED_SOURCES = {"ozon", "wb"}


def _problem(level: str, message: str, product_key: str | None = None, **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "level": level,
        "product_key": product_key,
        "message": message,
    }
    item.update({key: value for key, value in extra.items() if value not in (None, "", [], {})})
    return item


def _validate_market_state(market_state: dict[str, Any]) -> dict[str, Any]:
    meta = market_state.get("meta", {}) or {}
    products = market_state.get("products", {}) or {}
    unmatched = market_state.get("unmatched_records", []) or []
    problems: list[dict[str, Any]] = []

    for error in meta.get("load_errors", []) or []:
        problems.append(_problem("critical", "market input file could not be loaded", file=error.get("file"), error=error.get("error")))

    for record in unmatched:
        problems.append(
            _problem(
                "critical",
                "market record was not matched to any master product",
                source=record.get("source"),
                source_file=record.get("source_file"),
                source_row=record.get("source_row"),
                title=record.get("title"),
                url=record.get("url"),
            )
        )

    for product_key, market in products.items():
        if market.get("sellable") is not True:
            continue

        for field in _REQUIRED_SELLABLE_FIELDS:
            if market.get(field) in (None, ""):
                problems.append(_problem("critical", f"sellable product is missing {field}", product_key=product_key))

        if int(market.get("market_price") or 0) <= 0:
            problems.append(_problem("critical", "sellable product has bad market_price", product_key=product_key, market_price=market.get("market_price")))

        if int(market.get("stock") or 0) <= 0:
            problems.append(_problem("critical", "sellable product has bad stock", product_key=product_key, stock=market.get("stock")))

        source = str(market.get("market_price_source") or "").lower()
        if source in _URL_REQUIRED_SOURCES and not market.get("market_url"):
            problems.append(_problem("critical", "Ozon/WB sellable product is missing market_url", product_key=product_key, source=source))
        elif source == "manual" and not market.get("market_url"):
            problems.append(_problem("cosmetic", "manual sellable product is missing market_url", product_key=product_key, source=source))

    return {
        "checked_at": now_iso(),
        "total_input_files": int(meta.get("total_input_files") or 0),
        "total_records": int(meta.get("total_records") or 0),
        "matched_records": int(meta.get("matched_records") or 0),
        "unmatched_records": int(meta.get("unmatched_records") or 0),
        "products_with_market": int(meta.get("products_with_market") or 0),
        "sellable_products": int(meta.get("sellable_products") or 0),
        "sources": meta.get("sources", {}) or {},
        "critical_count": sum(1 for item in problems if item.get("level") == "critical"),
        "cosmetic_count": sum(1 for item in problems if item.get("level") == "cosmetic"),
        "problems": problems,
        "note": "Header-only market files are allowed. Active Ozon/WB sellable rows must have price, stock, availability and market_url.",
    }


def _txt_report(report: dict[str, Any]) -> str:
    lines = [
        "CS-Kaspi market input validation",
        f"checked_at: {report.get('checked_at')}",
        f"total_input_files: {report.get('total_input_files')}",
        f"total_records: {report.get('total_records')}",
        f"matched_records: {report.get('matched_records')}",
        f"unmatched_records: {report.get('unmatched_records')}",
        f"products_with_market: {report.get('products_with_market')}",
        f"sellable_products: {report.get('sellable_products')}",
        f"sources: {report.get('sources')}",
        f"critical_count: {report.get('critical_count')}",
        f"cosmetic_count: {report.get('cosmetic_count')}",
        "",
        "problems:",
    ]
    for item in report.get("problems", [])[:500]:
        parts = [f"[{item.get('level')}]", str(item.get("message"))]
        if item.get("product_key"):
            parts.append(f"product_key={item.get('product_key')}")
        if item.get("source"):
            parts.append(f"source={item.get('source')}")
        if item.get("source_file"):
            parts.append(f"file={item.get('source_file')}")
        if item.get("source_row"):
            parts.append(f"row={item.get('source_row')}")
        lines.append("  " + " | ".join(parts))
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    ensure_runtime_dirs()
    state_dir = path_from_config("artifacts_state_dir")
    reports_dir = path_from_config("artifacts_reports_dir")
    market_state = read_json(state_dir / "market_state.json", required=True)
    report = _validate_market_state(market_state)
    write_json(reports_dir / "market_input_validation.json", report)
    (reports_dir / "market_input_validation.txt").write_text(_txt_report(report), encoding="utf-8")
    if report["critical_count"]:
        raise RuntimeError(f"Market input validation failed: {report['critical_count']} critical issue(s). See artifacts/reports/market_input_validation.txt")
    return report


if __name__ == "__main__":
    run()
