from __future__ import annotations
from pathlib import Path
from typing import Any
import yaml

def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
