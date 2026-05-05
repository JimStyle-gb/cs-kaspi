from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from scripts.cs_kaspi.catalog.apply_model_specs import run as apply_model_specs
from scripts.cs_kaspi.catalog.load_official_states import run as load_official_states
from scripts.cs_kaspi.catalog.merge_products import run as merge_products
from scripts.cs_kaspi.core.time_utils import now_iso
from scripts.cs_kaspi.kaspi_policy.build_offer import run as build_kaspi_offer

from .load_existing_records import run as load_existing_records
from .match_existing_records import run as match_existing_records


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "kaspi_product_id": record.get("kaspi_product_id"),
        "kaspi_sku": record.get("kaspi_sku"),
        "kaspi_title": record.get("kaspi_title"),
        "kaspi_url": record.get("kaspi_url"),
        "kaspi_price": record.get("kaspi_price"),
        "kaspi_stock": record.get("kaspi_stock"),
        "kaspi_available": record.get("kaspi_available"),
        "matched_by": record.get("matched_by"),
        "match_confidence": record.get("match_confidence"),
        "source_file": record.get("source_file"),
        "source_row": record.get("source_row"),
    }


def _choose_best_record(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not records:
        return None
    return sorted(
        records,
        key=lambda r: (
            -int(r.get("match_confidence") or 0),
            0 if r.get("kaspi_product_id") else 1,
            0 if r.get("kaspi_sku") else 1,
            int(r.get("source_row") or 10**9),
        ),
    )[0]


def _product_match(records: list[dict[str, Any]]) -> dict[str, Any]:
    best = _choose_best_record(records)
    if not best:
        return _empty_match()
    return {
        "exists": True,
        "kaspi_product_id": best.get("kaspi_product_id"),
        "kaspi_sku": best.get("kaspi_sku"),
        "kaspi_title": best.get("kaspi_title"),
        "kaspi_url": best.get("kaspi_url"),
        "kaspi_price": best.get("kaspi_price"),
        "kaspi_stock": best.get("kaspi_stock"),
        "kaspi_available": best.get("kaspi_available"),
        "matched_by": best.get("matched_by"),
        "confidence": best.get("match_confidence"),
        "source_file": best.get("source_file"),
        "source_row": best.get("source_row"),
        "records_count": len(records),
        "records": [_public_record(r) for r in records[:10]],
    }


def _empty_match() -> dict[str, Any]:
    return {
        "exists": False,
        "kaspi_product_id": None,
        "kaspi_sku": None,
        "kaspi_title": None,
        "kaspi_url": None,
        "kaspi_price": None,
        "kaspi_stock": None,
        "kaspi_available": None,
        "matched_by": None,
        "confidence": None,
        "records_count": 0,
    }


def _products_for_matching() -> list[dict[str, Any]]:
    official_states = load_official_states(required=True)
    products = apply_model_specs(merge_products(official_states))
    prepared: list[dict[str, Any]] = []
    for product in products:
        offer = build_kaspi_offer({**product, "market": {}})
        product["kaspi_policy"] = {"kaspi_title": offer.get("kaspi_policy", {}).get("kaspi_title")}
        prepared.append(product)
    return prepared


def run() -> dict[str, Any]:
    products = _products_for_matching()
    loaded = load_existing_records()
    matched_records = match_existing_records(products, loaded.get("records", []))

    records_by_product: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unmatched: list[dict[str, Any]] = []
    for record in matched_records:
        product_key = record.get("matched_product_key")
        if product_key:
            records_by_product[product_key].append(record)
        else:
            unmatched.append(_public_record(record))

    products_state = {
        product_key: _product_match(records)
        for product_key, records in sorted(records_by_product.items())
    }
    methods = Counter(record.get("matched_by") for record in matched_records if record.get("matched_by"))

    return {
        "meta": {
            "built_at": now_iso(),
            "total_input_files": len(loaded.get("files", [])),
            "total_records": len(loaded.get("records", [])),
            "matched_records": sum(1 for r in matched_records if r.get("matched_product_key")),
            "unmatched_records": len(unmatched),
            "matched_products": len(products_state),
            "match_methods": dict(methods),
            "load_errors": loaded.get("errors", []),
            "note": "Kaspi match layer only marks existing products. It does not send anything to Kaspi API.",
        },
        "products": products_state,
        "unmatched_records": unmatched,
    }
