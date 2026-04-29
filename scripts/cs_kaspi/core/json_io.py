from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path, default: Any = None, required: bool = False) -> Any:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required JSON file not found: {path}")
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: Any, pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        if pretty:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        else:
            json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
