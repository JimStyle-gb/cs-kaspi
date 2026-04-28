from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.paths import path_from_config
from scripts.cs_kaspi.core.yaml_io import read_yaml

_ALLOWED_SUFFIXES = {".json", ".yml", ".yaml", ".csv"}
_IGNORED_NAME_PARTS = {"example", "sample", "readme", "template"}
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
    if text in {"1", "true", "yes", "y", "да", "есть", "active", "available", "in_stock", "в наличии"}:
        return True
    if text in {"0", "false", "no", "n", "нет", "inactive", "blocked", "archived", "out_of_stock", "нет в наличии"}:
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


def _records_from_loaded(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("products", "records", "items", "offers", "kaspi_products", "existing_products"):
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


def _iter_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        return []
    files: list[Path] = []
    for path in input_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _ALLOWED_SUFFIXES:
            continue
        name = path.name.lower()
        if any(part in name for part in _IGNORED_NAME_PARTS):
            continue
        files.append(path)
    return sorted(files)


def _first(record: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in record and record.get(key) not in (None, ""):
            return record.get(key)
    return None


def _normalize_record(raw: dict[str, Any], *, path: Path, row_number: int) -> dict[str, Any]:
    product_key = _clean_str(_first(raw, ("product_key", "cs_product_key", "external_id", "externalId")))
    kaspi_sku = _clean_str(_first(raw, ("kaspi_sku", "sku", "merchant_sku", "offer_id", "offerId", "code", "vendor_code")))
    kaspi_product_id = _clean_str(_first(raw, ("kaspi_product_id", "product_id", "kaspi_id", "id", "master_product_id")))
    title = _clean_str(_first(raw, ("kaspi_title", "title", "name", "product_name", "Наименование", "Название")))

    return {
        "source_file": str(path.as_posix()),
        "source_row": row_number,
        "product_key": product_key,
        "kaspi_sku": kaspi_sku,
        "kaspi_product_id": kaspi_product_id,
        "supplier_key": _clean_str(_first(raw, ("supplier_key", "supplier"))),
        "category_key": _clean_str(_first(raw, ("category_key", "category"))),
        "brand": _clean_str(_first(raw, ("brand", "Бренд"))),
        "model_key": _clean_str(_first(raw, ("model_key", "model"))),
        "variant_key": _clean_str(_first(raw, ("variant_key", "variant", "color_key"))),
        "official_article": _clean_str(_first(raw, ("official_article", "article", "vendorCode", "vendor_code", "manufacturer_sku"))),
        "kaspi_title": title,
        "kaspi_url": _clean_str(_first(raw, ("kaspi_url", "url", "link", "product_url"))),
        "kaspi_price": _parse_price(_first(raw, ("kaspi_price", "price", "current_price"))),
        "kaspi_stock": _parse_int(_first(raw, ("kaspi_stock", "stock", "quantity", "qty"))),
        "kaspi_available": _parse_bool(_first(raw, ("kaspi_available", "available", "status", "active"))),
        "raw": raw,
    }


def run() -> dict[str, Any]:
    input_dir = path_from_config("input_kaspi_existing_dir")
    files = _iter_files(input_dir)
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for path in files:
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
            records.append(_normalize_record(raw, path=path, row_number=idx))

    return {
        "input_dir": str(input_dir.as_posix()),
        "files": [str(p.as_posix()) for p in files],
        "records": records,
        "errors": errors,
    }
