from __future__ import annotations

import csv
from typing import Any

from scripts.cs_kaspi.core.json_io import read_json, write_json
from scripts.cs_kaspi.core.paths import path_from_config
from scripts.cs_kaspi.core.time_utils import now_iso

CSV_HEADERS = [
    "product_key",
    "kaspi_sku",
    "kaspi_product_id",
    "kaspi_title",
    "kaspi_url",
    "kaspi_price",
    "kaspi_stock",
    "kaspi_available",
    "supplier_key",
    "category_key",
    "brand",
    "model_key",
    "variant_key",
    "official_article",
    "official_url",
    "official_title",
]


def _row(product: dict[str, Any]) -> dict[str, Any]:
    official = product.get("official", {}) or {}
    kaspi = product.get("kaspi_policy", {}) or {}
    return {
        "product_key": product.get("product_key"),
        "kaspi_sku": product.get("product_key"),
        "kaspi_product_id": "",
        "kaspi_title": kaspi.get("kaspi_title"),
        "kaspi_url": "",
        "kaspi_price": "",
        "kaspi_stock": "",
        "kaspi_available": "",
        "supplier_key": product.get("supplier_key"),
        "category_key": product.get("category_key"),
        "brand": product.get("brand"),
        "model_key": product.get("model_key"),
        "variant_key": product.get("variant_key"),
        "official_article": official.get("product_id"),
        "official_url": official.get("url"),
        "official_title": official.get("title_official"),
    }


def _write_csv(path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_HEADERS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in CSV_HEADERS})


def _readme(total: int) -> str:
    return (
        "CS-Kaspi Kaspi existing-products template\n"
        "\n"
        f"Rows: {total}\n"
        "\n"
        "How to use:\n"
        "1. Copy kaspi_existing_template.csv to input/kaspi/existing/current_kaspi_products.csv.\n"
        "2. Keep product_key and kaspi_sku unchanged when possible.\n"
        "3. Fill kaspi_product_id / kaspi_url / kaspi_price / kaspi_stock if you have them.\n"
        "4. Run Build_All. Existing products will become update_candidates, new products will remain create_candidates.\n"
        "\n"
        "This template is only for matching existing Kaspi products. It does not send anything to Kaspi API.\n"
    )


def run() -> dict[str, Any]:
    state_dir = path_from_config("artifacts_state_dir")
    out_dir = path_from_config("artifacts_kaspi_match_templates_dir")
    catalog = read_json(state_dir / "master_catalog.json", required=True)
    products = [p for p in catalog.get("products", []) if isinstance(p, dict)]
    rows = [_row(p) for p in products]

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "kaspi_existing_template.csv"
    json_path = out_dir / "kaspi_existing_template.json"
    readme_path = out_dir / "README.txt"

    _write_csv(csv_path, rows)
    write_json(json_path, {"meta": {"built_at": now_iso(), "total_products": len(rows)}, "products": rows})
    readme_path.write_text(_readme(len(rows)), encoding="utf-8")

    return {
        "total_products": len(rows),
        "files": {
            "csv": "artifacts/kaspi_match_templates/kaspi_existing_template.csv",
            "json": "artifacts/kaspi_match_templates/kaspi_existing_template.json",
            "readme": "artifacts/kaspi_match_templates/README.txt",
        },
    }


if __name__ == "__main__":
    run()
