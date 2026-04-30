from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from scripts.cs_kaspi.core.json_io import write_json
from scripts.cs_kaspi.core.yaml_io import write_yaml


def write_preview_json(path: Path, preview: dict) -> None:
    write_json(path, preview)


def write_preview_yml(path: Path, preview: dict) -> None:
    write_yaml(path, preview)


def write_preview_txt(path: Path, preview: dict) -> None:
    lines = ["CS-Kaspi preview", f"total_products: {preview.get('meta', {}).get('total_products', 0)}", ""]
    for p in preview.get("products", []):
        lines.extend([
            f"PRODUCT: {p.get('product_key')}",
            f"  supplier: {p.get('supplier_key')}",
            f"  category: {p.get('category_key')} / {p.get('supplier_category_name')}",
            f"  official_title: {p.get('official_title')}",
            f"  official_url: {p.get('official_url')}",
            f"  official_price: {p.get('official_price')}",
            f"  market_sellable: {p.get('market_sellable')}",
            f"  market_reason: {p.get('market_sellable_reason')}",
            f"  market_price: {p.get('market_price')}",
            f"  market_source: {p.get('market_price_source')}",
            f"  market_url: {p.get('market_url')}",
            f"  kaspi_title: {p.get('kaspi_title')}",
            f"  kaspi_price: {p.get('kaspi_price')}",
            f"  stock: {p.get('kaspi_stock')}",
            f"  lead_time_days: {p.get('lead_time_days')}",
            f"  images_count: {p.get('images_count')}",
            f"  attributes_count: {p.get('attributes_count')}",
            f"  status: {p.get('lifecycle_status')} / {p.get('action_status')}",
            f"  review: {p.get('review_reasons')}",
            "",
        ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_preview_xml(path: Path, preview: dict) -> None:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<preview>']
    lines.append(f'  <total_products>{preview.get("meta", {}).get("total_products", 0)}</total_products>')
    for p in preview.get("products", []):
        lines.append('  <product>')
        for key, value in p.items():
            if isinstance(value, list):
                value = ", ".join(str(x) for x in value)
            lines.append(f"    <{key}>{escape(str(value or ''))}</{key}>")
        lines.append('  </product>')
    lines.append('</preview>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(preview_dir: Path, preview: dict) -> None:
    write_preview_json(preview_dir / "kaspi_preview.json", preview)
    write_preview_yml(preview_dir / "kaspi_preview.yml", preview)
    write_preview_xml(preview_dir / "kaspi_preview.xml", preview)
    write_preview_txt(preview_dir / "kaspi_preview.txt", preview)
