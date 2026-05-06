from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from scripts.cs_kaspi.core.paths import ROOT


REFERENCE_PATH = ROOT / "data" / "kaspi" / "reference" / "kaspi_categories.json"


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


@lru_cache(maxsize=1)
def load_category_reference() -> dict[str, dict[str, Any]]:
    """Load Kaspi category reference exported from Seller API.

    The file is a public category dictionary (code/title), not a secret. API tokens must never be stored here.
    """
    if not REFERENCE_PATH.exists():
        return {}
    try:
        data = json.loads(REFERENCE_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}

    rows: list[Any]
    if isinstance(data, dict) and isinstance(data.get("value"), list):
        rows = data.get("value") or []
    elif isinstance(data, list):
        rows = data
    else:
        rows = []

    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = _clean(row.get("code"))
        if code:
            result[code] = dict(row)
    return result


def lookup_category_code(code: Any) -> dict[str, Any]:
    clean_code = _clean(code)
    if not clean_code:
        return {}
    return load_category_reference().get(clean_code, {})
