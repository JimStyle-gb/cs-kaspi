from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.time_utils import now_iso
from .utils import category_dirs


def run() -> dict[str, Any]:
    manuals_dir = category_dirs()["manuals"]
    manuals = [str(path) for path in manuals_dir.glob("*.pdf")]
    return {
        "supplier_key": "demiand",
        "fetched_at": now_iso(),
        "manuals": manuals,
    }
