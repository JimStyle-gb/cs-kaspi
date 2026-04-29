from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.paths import path_from_config


def _records_from_loaded(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("records", "products", "items", "offers", "market_records"):
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        return [data]
    return []


def _normalize_record(raw: dict[str, Any], *, path: Path, row_number: int) -> dict[str, Any]:
    def clean(value: Any) -> str | None:
        if value in (None, ""):
            return None
        return str(value).strip()

    def parse_int(value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(float(str(value).replace(" ", "").replace(",", ".")))
        except Exception:
            return None

    def parse_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if value in (None, ""):
            return None
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "y", "да", "available", "in_stock"}:
            return True
        if text in {"0", "false", "no", "n", "нет", "not_available", "out_of_stock"}:
            return False
        return None

    return {
        "source": clean(raw.get("source")) or "auto_discovery",
        "source_file": str(path.as_posix()),
        "source_row": row_number,
        "product_key": clean(raw.get("product_key")),
        "base_product_key": clean(raw.get("base_product_key")),
        "market_product_key": clean(raw.get("market_product_key")) or clean(raw.get("product_key")),
        "supplier_key": clean(raw.get("supplier_key")),
        "category_key": clean(raw.get("category_key")),
        "official_article": clean(raw.get("official_article")),
        "model_key": clean(raw.get("model_key")),
        "variant_key": clean(raw.get("variant_key")),
        "title": clean(raw.get("title") or raw.get("market_title")),
        "url": clean(raw.get("url")),
        "image": clean(raw.get("image")),
        "price": parse_int(raw.get("price")),
        "old_price": parse_int(raw.get("old_price")),
        "available": parse_bool(raw.get("available")),
        "stock": parse_int(raw.get("stock")),
        "eta_text": clean(raw.get("eta_text")),
        "lead_time_days": parse_int(raw.get("lead_time_days")),
        "market_color": clean(raw.get("market_color")),
        "market_bundle": clean(raw.get("market_bundle")),
        "market_variant_signature": clean(raw.get("market_variant_signature") or raw.get("variant_key")),
        "rating": clean(raw.get("rating")),
        "reviews_count": parse_int(raw.get("reviews_count")),
        "matched_by": clean(raw.get("matched_by")),
        "match_confidence": parse_int(raw.get("match_confidence")),
        "raw": raw,
    }


def _discovery_file() -> Path | None:
    discovery_dir = path_from_config("artifacts_market_discovery_dir")
    path = discovery_dir / "market_best_offers.json"
    return path if path.exists() else None


def run() -> dict[str, Any]:
    path = _discovery_file()
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    files: list[str] = []
    if path:
        files.append(str(path.as_posix()))
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            loaded = _records_from_loaded(data)
            for idx, raw in enumerate(loaded, start=1):
                records.append(_normalize_record(raw, path=path, row_number=idx))
        except Exception as exc:
            errors.append({"file": str(path.as_posix()), "error": str(exc)})
    return {
        "input_dir": str(path_from_config("artifacts_market_discovery_dir").as_posix()),
        "files": files,
        "records": records,
        "errors": errors,
    }
