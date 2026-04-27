from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.json_io import read_json
from scripts.cs_kaspi.core.paths import path_from_config
from scripts.cs_kaspi.exports.build_export_plan import run as build_export_plan
from scripts.cs_kaspi.exports.write_files import run as write_export_files


def run() -> dict[str, Any]:
    state_dir = path_from_config("artifacts_state_dir")
    catalog = read_json(state_dir / "master_catalog.json", required=True)
    if not isinstance(catalog, dict):
        raise RuntimeError("master_catalog.json must be a JSON object")
    products = catalog.get("products", [])
    if not products:
        raise RuntimeError("master_catalog.json has no products. Run build_master_catalog first.")

    plan = build_export_plan(catalog)
    files = write_export_files(plan)
    return {"meta": plan.get("meta", {}), "files": files}


if __name__ == "__main__":
    run()
