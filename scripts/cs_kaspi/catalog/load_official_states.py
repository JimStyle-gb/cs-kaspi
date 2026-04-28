from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.json_io import read_json
from scripts.cs_kaspi.core.suppliers import enabled_suppliers, supplier_state_path


def run(required: bool = True) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    missing: list[str] = []

    for supplier in enabled_suppliers():
        path = supplier_state_path(supplier)
        if not path.exists():
            missing.append(f"{supplier['supplier_key']}: {path}")
            continue
        state = read_json(path, required=True)
        states.append(state)

    if required and missing:
        raise FileNotFoundError(
            "Official supplier state files are missing. Run Build_All or Refresh_Official_Sources first. Missing: "
            + "; ".join(missing)
        )
    return states
