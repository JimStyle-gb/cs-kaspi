from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.json_io import read_json
from scripts.cs_kaspi.core.paths import ensure_runtime_dirs, path_from_config
from scripts.cs_kaspi.kaspi_delivery.build_create_api_payload import run as build_create_api_payload
from scripts.cs_kaspi.kaspi_delivery.build_delivery_summary import run as build_delivery_summary
from scripts.cs_kaspi.kaspi_delivery.build_price_stock_xml import run as build_price_stock_xml
from scripts.cs_kaspi.kaspi_delivery.write_files import run as write_delivery_files


def _products(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("products")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def run() -> dict[str, Any]:
    ensure_runtime_dirs()
    out_dir = path_from_config("artifacts_exports_dir")

    export_summary = read_json(out_dir / "kaspi_export_summary.json", required=True)
    create_source = read_json(out_dir / "kaspi_create_candidates.json", required=True)
    update_source = read_json(out_dir / "kaspi_update_candidates.json", required=True)
    pause_source = read_json(out_dir / "kaspi_pause_candidates.json", required=True)

    if not isinstance(export_summary, dict):
        raise RuntimeError("kaspi_export_summary.json must be a JSON object")

    create_payload = build_create_api_payload(_products(create_source), export_summary)
    price_stock = build_price_stock_xml(_products(update_source), _products(pause_source))
    summary = build_delivery_summary(
        export_meta=export_summary,
        create_payload=create_payload,
        price_stock=price_stock,
    )
    files = write_delivery_files(
        out_dir,
        create_payload=create_payload,
        price_stock=price_stock,
        summary=summary,
    )

    return {"meta": summary, "files": files}


if __name__ == "__main__":
    run()
