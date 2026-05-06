from __future__ import annotations

import importlib
from typing import Any

from scripts.cs_kaspi.core.json_io import write_json
from scripts.cs_kaspi.core.paths import ensure_runtime_dirs, path_from_config
from scripts.cs_kaspi.core.suppliers import enabled_suppliers
from scripts.cs_kaspi.core.time_utils import now_iso


def run() -> dict[str, Any]:
    ensure_runtime_dirs()
    suppliers_result: dict[str, Any] = {}
    for supplier in enabled_suppliers():
        supplier_key = supplier["supplier_key"]
        module = importlib.import_module(f"scripts.cs_kaspi.suppliers.{supplier_key}.build_supplier_state")
        suppliers_result[supplier_key] = module.run()

    state = {
        "checked_at": now_iso(),
        "suppliers": suppliers_result,
    }
    write_json(path_from_config("artifacts_state_dir") / "official_state.json", state)
    return state


if __name__ == "__main__":
    run()
