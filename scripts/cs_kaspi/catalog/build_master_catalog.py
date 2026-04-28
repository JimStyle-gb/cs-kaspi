from __future__ import annotations

from collections import Counter
from typing import Any

from scripts.cs_kaspi.core.hash_utils import stable_hash
from scripts.cs_kaspi.core.json_io import read_json
from scripts.cs_kaspi.core.paths import path_from_config
from scripts.cs_kaspi.core.time_utils import now_iso
from scripts.cs_kaspi.kaspi_policy.build_offer import run as build_kaspi_offer
from scripts.cs_kaspi.markets.apply_market_state import run as apply_market_state
from scripts.cs_kaspi.kaspi_match.apply_match_state import run as apply_kaspi_match_state

from .apply_model_specs import run as apply_model_specs
from .load_official_states import run as load_official_states
from .merge_products import run as merge_products
from .validate_master_catalog import run as validate_master_catalog


def _load_market_state() -> dict[str, Any]:
    state_dir = path_from_config("artifacts_state_dir")
    return read_json(state_dir / "market_state.json", default={"products": {}, "meta": {}})


def _load_kaspi_match_state() -> dict[str, Any]:
    state_dir = path_from_config("artifacts_state_dir")
    return read_json(state_dir / "kaspi_match_state.json", default={"products": {}, "meta": {}})


def build_summary(catalog: dict[str, Any]) -> dict[str, Any]:
    products = catalog.get("products", [])
    return {
        "built_at": catalog.get("meta", {}).get("built_at"),
        "total_products": len(products),
        "suppliers": dict(Counter(p.get("supplier_key") for p in products)),
        "categories": dict(Counter(p.get("category_key") for p in products)),
        "lifecycle_status": dict(Counter(p.get("status", {}).get("lifecycle_status") for p in products)),
        "action_status": dict(Counter(p.get("status", {}).get("action_status") for p in products)),
        "model_specs_exists": dict(Counter(bool(p.get("model_specs", {}).get("exists")) for p in products)),
        "market_sellable": dict(Counter(bool(p.get("market", {}).get("sellable")) for p in products)),
        "market_sources": dict(Counter(p.get("market", {}).get("market_price_source") for p in products if p.get("market", {}).get("market_price_source"))),
        "kaspi_match_exists": dict(Counter(bool(p.get("kaspi_match", {}).get("exists")) for p in products)),
        "kaspi_match_methods": dict(Counter(p.get("kaspi_match", {}).get("matched_by") for p in products if p.get("kaspi_match", {}).get("matched_by"))),
        "validation": catalog.get("validation", {}),
    }


def run() -> dict[str, Any]:
    official_states = load_official_states(required=True)
    products = merge_products(official_states)
    products = apply_model_specs(products)
    products = apply_market_state(products, _load_market_state())
    products = apply_kaspi_match_state(products, _load_kaspi_match_state())

    final_products: list[dict[str, Any]] = []
    for product in products:
        kaspi_offer = build_kaspi_offer(product)
        product["kaspi_policy"] = kaspi_offer["kaspi_policy"]
        product["status"] = kaspi_offer["status"]
        product["changes"] = {
            "official_hash": stable_hash(product.get("official", {})),
            "market_hash": stable_hash(product.get("market", {})),
            "kaspi_policy_hash": stable_hash(product.get("kaspi_policy", {})),
        }
        final_products.append(product)

    validation = validate_master_catalog(final_products)
    if not final_products:
        raise RuntimeError("Master catalog has 0 products. This is forbidden: check official state input files.")

    return {
        "meta": {
            "project_name": "CS-Kaspi",
            "built_at": now_iso(),
            "total_products": len(final_products),
            "suppliers": sorted(set(p.get("supplier_key") for p in final_products)),
            "categories": sorted(set(p.get("category_key") for p in final_products)),
        },
        "validation": validation,
        "products": final_products,
    }
