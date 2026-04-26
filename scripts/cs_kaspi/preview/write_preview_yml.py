from __future__ import annotations
from pathlib import Path
from scripts.cs_kaspi.core.write_yaml import write_yaml
def run(path: Path, preview: dict) -> None:
    write_yaml(path, preview)
