from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.catalog.build_master_catalog import build_summary
from scripts.cs_kaspi.catalog.build_master_catalog import run as build_master_catalog
from scripts.cs_kaspi.core.json_io import write_json
from scripts.cs_kaspi.core.paths import ensure_runtime_dirs, path_from_config


def run() -> dict[str, Any]:
    ensure_runtime_dirs()
    catalog = build_master_catalog()
    summary = build_summary(catalog)
    state_dir = path_from_config("artifacts_state_dir")
    write_json(state_dir / "master_catalog.json", catalog)
    write_json(state_dir / "master_catalog_summary.json", summary)
    return summary


if __name__ == "__main__":
    run()
