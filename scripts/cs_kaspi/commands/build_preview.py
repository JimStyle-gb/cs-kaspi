from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.json_io import read_json
from scripts.cs_kaspi.core.paths import ensure_runtime_dirs, path_from_config
from scripts.cs_kaspi.preview.build_preview import run as build_preview
from scripts.cs_kaspi.preview.write_files import run as write_preview_files


def run() -> dict[str, Any]:
    ensure_runtime_dirs()
    state_dir = path_from_config("artifacts_state_dir")
    preview_dir = path_from_config("artifacts_preview_dir")
    catalog = read_json(state_dir / "master_catalog.json", required=True)
    preview = build_preview(catalog)
    write_preview_files(preview_dir, preview)
    return preview.get("meta", {})


if __name__ == "__main__":
    run()
