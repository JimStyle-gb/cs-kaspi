from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from scripts.cs_kaspi.catalog.apply_model_specs import run as apply_model_specs
from scripts.cs_kaspi.catalog.load_official_states import run as load_official_states
from scripts.cs_kaspi.catalog.merge_products import run as merge_products
from scripts.cs_kaspi.core.time_utils import now_iso
from .load_market_records import run as load_market_records
from .match_market_records import run as match_market_records


def _is_available(record: dict[str, Any]) -> bool:
    if record.get("available") is False:
        return False
    if record.get("stock") is not None and int(record.get("stock") or 0) <= 0:
        return False
    return record.get("available") is True or record.get("price") is not None


def _choose_best_record(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    sellable = [r for r in records if _is_available(r) and r.get("price")]
    if sellable:
        return sorted(sellable, key=lambda r: (int(r.get("price") or 10**12), -int(r.get("match_confidence") or 0)))[0]
    priced = [r for r in records if r.get("price")]
    if priced:
        return sorted(priced, key=lambda r: (int(r.get("price") or 10**12), -int(r.get("match_confidence") or 0)))[0]
    return records[0] if records else None


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": record.get("source"),
        "title": record.get("title"),
        "url": record.get("url"),
        "price": record.get("price"),
        "price_currency": record.get("price_currency"),
        "old_price": record.get("old_price"),
        "available": record.get("available"),
        "stock": record.get("stock"),
        "lead_time_days": record.get("lead_time_days"),
        "rating": record.get("rating"),
        "reviews_count": record.get("reviews_count"),
        "matched_by": record.get("matched_by"),
        "official_match_status": record.get("official_match_status"),
        "match_confidence": record.get("match_confidence"),
        "source_file": record.get("source_file"),
        "source_row": record.get("source_row"),
        "base_product_key": record.get("base_product_key") or record.get("matched_base_product_key"),
        "market_product_key": record.get("market_product_key") or record.get("matched_product_key"),
        "market_color": record.get("market_color"),
        "market_bundle": record.get("market_bundle"),
        "market_variant_signature": record.get("market_variant_signature") or record.get("variant_key"),
    }


def _variant_fields(record: dict[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {}
    return {
        "base_product_key": record.get("base_product_key") or record.get("matched_base_product_key"),
        "market_product_key": record.get("market_product_key") or record.get("matched_product_key"),
        "market_color": record.get("market_color"),
        "market_bundle": record.get("market_bundle"),
        "market_variant_signature": record.get("market_variant_signature") or record.get("variant_key"),
        "market_title": record.get("title"),
        "market_image": record.get("image"),
        "supplier_key": record.get("supplier_key"),
        "category_key": record.get("category_key"),
        "brand": record.get("raw", {}).get("brand") if isinstance(record.get("raw"), dict) else None,
        "model_key": record.get("model_key"),
        "official_match_status": record.get("official_match_status"),
    }


def _product_market(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_source[str(record.get("source") or "manual")].append(record)

    sources: dict[str, Any] = {}
    available_candidates: list[dict[str, Any]] = []
    for source, source_records in sorted(by_source.items()):
        best = _choose_best_record(source_records)
        if best:
            sources[source] = _public_record(best)
            if _is_available(best) and best.get("price"):
                available_candidates.append(best)

    if available_candidates:
        # Price rule: for the exact same WB sellable variant, choose the lowest sellable price.
        # Stock and ETA must come from the same chosen offer, not from another seller/duplicate.
        best = sorted(available_candidates, key=lambda r: int(r.get("price") or 10**12))[0]
        best_stock = int(best.get("stock") or 0) if best.get("stock") is not None else 1
        best_lead_time = int(best.get("lead_time_days") or 0) if best.get("lead_time_days") else None
        return {
            "sources": sources,
            "sellable": True,
            "sellable_reason": "market_available",
            "market_price": int(best.get("price")),
            "market_price_source": best.get("source"),
            "market_url": best.get("url"),
            "market_image": best.get("image"),
            "stock": best_stock if best_stock > 0 else 1,
            # No safety buffer: selected market ETA is copied as-is when available. Missing ETA remains visible in meta.
            "lead_time_days": best_lead_time if best_lead_time else 3,
            "eta_status": "trusted_or_market_provided" if best_lead_time else "missing_market_eta_fallback_used",
            **_variant_fields(best),
        }

    if records:
        first = records[0]
        return {
            "sources": sources,
            "sellable": False,
            "sellable_reason": "market_records_found_but_not_available",
            "market_price": None,
            "market_price_source": None,
            "market_url": None,
            "market_image": first.get("image"),
            "stock": 0,
            "lead_time_days": 20,
            "eta_status": "not_sellable",
            **_variant_fields(first),
        }

    return {
        "sources": {},
        "sellable": False,
        "sellable_reason": "market_data_not_loaded",
        "market_price": None,
        "market_price_source": None,
        "market_url": None,
        "stock": 0,
        "lead_time_days": 20,
    }


def run() -> dict[str, Any]:
    official_states = load_official_states(required=True)
    products = apply_model_specs(merge_products(official_states))
    loaded = load_market_records()
    matched_records = match_market_records(products, loaded.get("records", []))

    records_by_product: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unmatched: list[dict[str, Any]] = []
    for record in matched_records:
        product_key = record.get("matched_product_key")
        if product_key:
            records_by_product[product_key].append(record)
        else:
            unmatched.append(_public_record(record))

    products_state = {
        product_key: _product_market(records)
        for product_key, records in sorted(records_by_product.items())
    }

    sources = Counter(record.get("source") for record in matched_records)
    return {
        "meta": {
            "built_at": now_iso(),
            "total_input_files": len(loaded.get("files", [])),
            "total_records": len(loaded.get("records", [])),
            "matched_records": sum(1 for r in matched_records if r.get("matched_product_key")),
            "unmatched_records": len(unmatched),
            "products_with_market": len(products_state),
            "sellable_products": sum(1 for p in products_state.values() if p.get("sellable") is True),
            "sources": dict(sources),
            "load_errors": loaded.get("errors", []),
        },
        "products": products_state,
        "unmatched_records": unmatched,
    }
