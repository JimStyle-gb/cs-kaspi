from __future__ import annotations

from scripts.cs_kaspi.core.file_paths import ensure_base_dirs, get_path
from scripts.cs_kaspi.core.read_json import read_json
from scripts.cs_kaspi.core.write_json import write_json

from scripts.cs_kaspi.catalog.merge_official_products import run as merge_official_products
from scripts.cs_kaspi.catalog.apply_model_specs import run as apply_model_specs
from scripts.cs_kaspi.catalog.build_master_catalog import run as build_master_catalog, build_summary
from scripts.cs_kaspi.markets.merge_market_data import run as merge_market_data
from scripts.cs_kaspi.kaspi_policy.build_kaspi_offer import run as build_kaspi_offer
from scripts.cs_kaspi.kaspi_policy.build_kaspi_status import run as build_kaspi_status


def _build_changes_block(product: dict) -> dict:
    official = product.get("official", {})
    market = product.get("market", {})
    kaspi = product.get("kaspi_policy", {})

    return {
        "last_checked_at": official.get("checked_at"),
        "last_changed_at": official.get("checked_at"),
        "official_hash": official.get("source_hash"),
        "market_hash": (market.get("ozon") or {}).get("source_hash") or (market.get("wb") or {}).get("source_hash"),
        "kaspi_hash": kaspi.get("offer_hash"),
        "changed_official": False,
        "changed_market": False,
        "changed_kaspi": False,
    }


def _build_meta_block(product: dict) -> dict:
    checked_at = (product.get("official") or {}).get("checked_at")
    return {
        "created_at": checked_at,
        "updated_at": checked_at,
        "notes": "",
    }


def run() -> dict:
    ensure_base_dirs()

    state_dir = get_path("artifacts_state_dir")
    official_products_payload = read_json(state_dir / "demiand_official_products.json", default={"products": []})
    official_products = official_products_payload.get("products", [])

    merged_products = merge_official_products([official_products])
    products_with_model_specs = apply_model_specs(merged_products, model_specs=None)
    products_with_market = merge_market_data(products_with_model_specs)

    final_products: list[dict] = []
    for product in products_with_market:
        row = dict(product)
        row["kaspi_policy"] = build_kaspi_offer(row)
        row["status"] = build_kaspi_status(row)
        row["changes"] = _build_changes_block(row)
        row["kaspi_match"] = {
            "exists_in_kaspi": False,
            "match_status": "not_matched",
            "kaspi_product_id": None,
            "match_confidence": "none",
        }
        row["meta"] = _build_meta_block(row)
        final_products.append(row)

    suppliers = sorted({p.get("supplier_key") for p in final_products if p.get("supplier_key")})
    categories = sorted({p.get("category_key") for p in final_products if p.get("category_key")})

    catalog = build_master_catalog(final_products, suppliers, categories)
    write_json(state_dir / "master_catalog.json", catalog)

    summary = build_summary(catalog)
    write_json(state_dir / "master_catalog_summary.json", summary)

    return catalog


if __name__ == "__main__":
    run()
