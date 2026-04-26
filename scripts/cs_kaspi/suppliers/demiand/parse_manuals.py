from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.core.time_utils import now_iso


def run(manual_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "supplier_key": "demiand",
        "parsed_at": now_iso(),
        "manuals_count": len(manual_payload.get("manuals", [])),
        "models": {},
    }
