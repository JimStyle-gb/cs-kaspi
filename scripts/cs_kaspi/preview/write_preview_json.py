from __future__ import annotations
from pathlib import Path
from scripts.cs_kaspi.core.write_json import write_json
def run(path: Path, preview: dict) -> None:
    write_json(path, preview)
