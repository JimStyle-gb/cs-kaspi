from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.json_io import read_json, write_json
from scripts.cs_kaspi.core.paths import ensure_runtime_dirs, path_from_config
from scripts.cs_kaspi.kaspi_delivery.build_test3_plan import run as build_test3_plan


def _products(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("products")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def run() -> dict[str, Any]:
    ensure_runtime_dirs()
    out_dir = path_from_config("artifacts_exports_dir")

    create_source = read_json(out_dir / "kaspi_create_candidates.json", required=True)
    update_source = read_json(out_dir / "kaspi_update_candidates.json", required=True)
    pause_source = read_json(out_dir / "kaspi_pause_candidates.json", required=True)
    delivery_summary = read_json(out_dir / "kaspi_delivery_summary.json", default={})

    plan = build_test3_plan(
        create_candidates=_products(create_source),
        update_candidates=_products(update_source),
        pause_candidates=_products(pause_source),
        delivery_summary=delivery_summary if isinstance(delivery_summary, dict) else {},
    )

    json_path = out_dir / "kaspi_test3_plan.json"
    txt_path = out_dir / "kaspi_test3_preview.txt"
    write_json(json_path, {key: value for key, value in plan.items() if key != "preview_text"})
    txt_path.write_text(str(plan.get("preview_text") or ""), encoding="utf-8")

    return {
        "meta": {key: value for key, value in plan.items() if key in {"meta", "candidate_counts", "readiness"}},
        "files": {
            "test3_plan_json": json_path.as_posix(),
            "test3_preview_txt": txt_path.as_posix(),
        },
    }


if __name__ == "__main__":
    run()
