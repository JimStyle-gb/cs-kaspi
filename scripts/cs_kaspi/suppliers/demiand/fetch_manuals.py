from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.time_utils import now_iso


def run() -> dict[str, Any]:
    return {
        "supplier_key": "demiand",
        "fetched_at": now_iso(),
        "manuals_count": 0,
        "manuals": [],
    }
