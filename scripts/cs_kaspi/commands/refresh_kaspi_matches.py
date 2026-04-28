from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.json_io import write_json
from scripts.cs_kaspi.core.paths import ensure_runtime_dirs, path_from_config
from scripts.cs_kaspi.kaspi_match.build_match_state import run as build_match_state


def _txt_report(state: dict[str, Any]) -> str:
    meta = state.get("meta", {}) or {}
    lines = [
        "CS-Kaspi Kaspi match report",
        f"built_at: {meta.get('built_at')}",
        f"total_input_files: {meta.get('total_input_files')}",
        f"total_records: {meta.get('total_records')}",
        f"matched_records: {meta.get('matched_records')}",
        f"unmatched_records: {meta.get('unmatched_records')}",
        f"matched_products: {meta.get('matched_products')}",
        "",
        "match_methods:",
    ]
    for key, value in (meta.get("match_methods") or {}).items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("load_errors:")
    errors = meta.get("load_errors") or []
    if not errors:
        lines.append("  none")
    else:
        for item in errors:
            lines.append(f"  {item.get('file')}: {item.get('error')}")
    lines.append("")
    lines.append("unmatched_records_sample:")
    unmatched = state.get("unmatched_records") or []
    if not unmatched:
        lines.append("  none")
    else:
        for idx, record in enumerate(unmatched[:50], start=1):
            lines.append(
                "  "
                + f"{idx}. sku={record.get('kaspi_sku')} | "
                + f"id={record.get('kaspi_product_id')} | "
                + str(record.get("kaspi_title") or "")
            )
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    ensure_runtime_dirs()
    state_dir = path_from_config("artifacts_state_dir")
    reports_dir = path_from_config("artifacts_reports_dir")
    state = build_match_state()

    write_json(state_dir / "kaspi_match_state.json", state)
    write_json(reports_dir / "kaspi_unmatched_existing_records.json", {"records": state.get("unmatched_records", [])})
    (reports_dir / "kaspi_match_report.txt").write_text(_txt_report(state), encoding="utf-8")
    return state.get("meta", {}) or {}


if __name__ == "__main__":
    run()
