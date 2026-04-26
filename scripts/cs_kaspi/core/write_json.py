from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def write_json(path: Path, data: Any, pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2 if pretty else None)
    path.write_text(text, encoding="utf-8")
