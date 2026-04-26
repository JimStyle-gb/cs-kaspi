from __future__ import annotations
import re

def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()

def slugify(value: str) -> str:
    value = normalize_spaces(value).lower()
    value = re.sub(r"[^a-zа-я0-9]+", "_", value)
    return value.strip("_")
