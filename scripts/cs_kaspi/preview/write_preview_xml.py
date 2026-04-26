from __future__ import annotations
from pathlib import Path
def run(path: Path, preview: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines=["<preview>"]
    for item in preview.get("products",[]):
        lines.append(f'  <product key="{item.get("product_key","")}">')
        lines.append(f'    <title>{item.get("kaspi_title","")}</title>')
        lines.append("  </product>")
    lines.append("</preview>")
    path.write_text("\n".join(lines), encoding="utf-8")
