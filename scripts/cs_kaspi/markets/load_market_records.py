from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.paths import path_from_config
from scripts.cs_kaspi.core.yaml_io import read_yaml

_ALLOWED_SUFFIXES = {".json", ".yml", ".yaml", ".csv"}
_IGNORED_NAME_PARTS = {"example", "sample", "readme"}
_IGNORED_DIR_PARTS = {"worklists", "templates"}
_PRICE_RE = re.compile(r"[^0-9.,]")


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "да", "есть", "available", "in_stock", "instock", "в наличии"}:
        return True
    if text in {"0", "false", "no", "n", "нет", "not_available", "out_of_stock", "outofstock", "нет в наличии"}:
        return False
    return None


def _parse_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        number = int(float(str(value).strip().replace(" ", "").replace(",", ".")))
        return number if number >= 0 else None
    except Exception:
        return None


def _parse_price(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = int(round(float(value)))
        return number if number > 0 else None
    text = _PRICE_RE.sub("", str(value)).replace(" ", "")
    if not text:
        return None
    if text.count(",") == 1 and text.count(".") == 0:
        text = text.replace(",", ".")
    if text.count(".") > 1:
        text = text.replace(".", "")
    try:
        number = int(round(float(text)))
        return number if number > 0 else None
    except Exception:
        return None


def _source_from_path(path: Path) -> str:
    parts = [p.lower() for p in path.parts]
    for source in ("ozon", "wb", "wildberries", "manual"):
        if source in parts:
            return "wb" if source == "wildberries" else source
    stem = path.stem.lower()
    if stem.startswith("ozon"):
        return "ozon"
    if stem.startswith(("wb", "wildberries")):
        return "wb"
    return "manual"


def _records_from_loaded(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("products", "records", "items", "offers", "market_records"):
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        return [data]
    return []


def _load_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return _records_from_loaded(data)


def _load_yaml(path: Path) -> list[dict[str, Any]]:
    return _records_from_loaded(read_yaml(path))


def _load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _iter_market_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        return []
    files: list[Path] = []
    for path in input_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _ALLOWED_SUFFIXES:
            continue
        name = path.name.lower()
        lower_parts = {part.lower() for part in path.parts}
        if lower_parts & _IGNORED_DIR_PARTS:
            continue
        if any(part in name for part in _IGNORED_NAME_PARTS):
            continue
        files.append(path)
    return sorted(files)


def _first(record: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in record and record.get(key) not in (None, ""):
            return record.get(key)
    return None


def _normalize_record(raw: dict[str, Any], *, source: str, path: Path, row_number: int) -> dict[str, Any]:
    record_source = _clean_str(_first(raw, ("source", "market", "market_source"))) or source
    if record_source.lower() == "wildberries":
        record_source = "wb"

    available = _parse_bool(_first(raw, ("available", "in_stock", "is_available", "presence", "status")))
    stock = _parse_int(_first(raw, ("stock", "quantity", "qty", "available_quantity")))
    if available is None and stock is not None:
        available = stock > 0

    price = _parse_price(_first(raw, ("price", "current_price", "sale_price", "market_price", "final_price")))
    old_price = _parse_price(_first(raw, ("old_price", "base_price", "regular_price", "original_price")))

    return {
        "source": str(record_source).strip().lower(),
        "source_file": str(path.as_posix()),
        "source_row": row_number,
        "product_key": _clean_str(_first(raw, ("product_key", "cs_product_key"))),
        "supplier_key": _clean_str(_first(raw, ("supplier_key", "supplier"))),
        "category_key": _clean_str(_first(raw, ("category_key", "category"))),
        "official_article": _clean_str(_first(raw, ("official_article", "article", "sku", "vendor_code", "product_id"))),
        "model_key": _clean_str(_first(raw, ("model_key", "model"))),
        "variant_key": _clean_str(_first(raw, ("variant_key", "variant", "color_key"))),
        "title": _clean_str(_first(raw, ("title", "name", "market_title", "product_name"))),
        "url": _clean_str(_first(raw, ("url", "link", "market_url", "product_url"))),
        "price": price,
        "old_price": old_price,
        "available": available,
        "stock": stock,
        "lead_time_days": _parse_int(_first(raw, ("lead_time_days", "delivery_days", "lead_time"))),
        "rating": _clean_str(_first(raw, ("rating", "stars"))),
        "reviews_count": _parse_int(_first(raw, ("reviews_count", "reviews", "feedbacks"))),
        "raw": raw,
    }


def run() -> dict[str, Any]:
    input_dir = path_from_config("input_market_dir")
    files = _iter_market_files(input_dir)
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for path in files:
        source = _source_from_path(path.relative_to(input_dir))
        try:
            if path.suffix.lower() == ".json":
                loaded = _load_json(path)
            elif path.suffix.lower() in {".yml", ".yaml"}:
                loaded = _load_yaml(path)
            else:
                loaded = _load_csv(path)
        except Exception as exc:
            errors.append({"file": str(path.as_posix()), "error": str(exc)})
            continue

        for idx, raw in enumerate(loaded, start=1):
            records.append(_normalize_record(raw, source=source, path=path, row_number=idx))

    return {
        "input_dir": str(input_dir.as_posix()),
        "files": [str(p.as_posix()) for p in files],
        "records": records,
        "errors": errors,
    }
