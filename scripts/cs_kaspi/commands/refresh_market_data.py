from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.json_io import write_json
from scripts.cs_kaspi.core.paths import ensure_runtime_dirs, path_from_config
from scripts.cs_kaspi.markets.build_market_state import run as build_market_state


def _txt_report(market_state: dict[str, Any]) -> str:
    meta = market_state.get("meta", {}) or {}
    lines = [
        "CS-Kaspi market report",
        f"built_at: {meta.get('built_at')}",
        f"total_input_files: {meta.get('total_input_files')}",
        f"total_records: {meta.get('total_records')}",
        f"matched_records: {meta.get('matched_records')}",
        f"unmatched_records: {meta.get('unmatched_records')}",
        f"products_with_market: {meta.get('products_with_market')}",
        f"sellable_products: {meta.get('sellable_products')}",
        f"sources: {meta.get('sources')}",
        "",
        "unmatched_records:",
    ]
    for record in market_state.get("unmatched_records", [])[:300]:
        lines.append(f"  [{record.get('source')}] row={record.get('source_row')} price={record.get('price')} title={record.get('title')} url={record.get('url')}")
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    ensure_runtime_dirs()
    state_dir = path_from_config("artifacts_state_dir")
    reports_dir = path_from_config("artifacts_reports_dir")
    market_state = build_market_state()
    write_json(state_dir / "market_state.json", market_state)
    (reports_dir / "market_report.txt").write_text(_txt_report(market_state), encoding="utf-8")
    write_json(reports_dir / "market_unmatched_records.json", market_state.get("unmatched_records", []))
    return market_state.get("meta", {})


if __name__ == "__main__":
    run()
