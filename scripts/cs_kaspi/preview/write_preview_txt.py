from __future__ import annotations
from pathlib import Path
def run(path: Path, preview: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines=["CS-Kaspi Preview", f'Products: {len(preview.get("products",[]))}', ""]
    for item in preview.get("products",[]):
        lines.append(f'- {item.get("product_key")} | {item.get("action_status")} | {item.get("kaspi_title")}')
    path.write_text("\n".join(lines), encoding="utf-8")
