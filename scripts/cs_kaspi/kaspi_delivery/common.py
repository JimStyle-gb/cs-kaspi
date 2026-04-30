from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.paths import ROOT

_SKU_ALLOWED_RE = re.compile(r"[^A-Za-z0-9]+")
_SUPPLIER_CODE_RE = re.compile(r"[^A-Za-z0-9]+")
_VALID_SKU_RE = re.compile(r"^[A-Za-z0-9]{1,20}$")


def safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def int_or_zero(value: Any) -> int:
    try:
        if value in (None, ""):
            return 0
        return int(float(str(value).replace(" ", "").replace(",", ".")))
    except Exception:
        return 0


def bool_yes_no(value: Any) -> str:
    return "yes" if value is True or str(value).strip().lower() in {"1", "true", "yes", "y", "да"} else "no"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except Exception:
        return path.as_posix()


def clean_sku(value: Any) -> str:
    return _SKU_ALLOWED_RE.sub("", text(value).upper())


def valid_kaspi_sku(value: Any) -> bool:
    return bool(_VALID_SKU_RE.fullmatch(text(value)))


def supplier_code(value: Any) -> str:
    raw = _SUPPLIER_CODE_RE.sub("", text(value).upper())
    if not raw:
        return "GEN"
    return (raw[:3]).ljust(3, "X")


def stable_hash(value: Any, length: int = 8) -> str:
    raw = text(value) or "missing"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest().upper()[:length]


def delivery_sku(item: dict[str, Any]) -> tuple[str, str]:
    """Возвращает безопасный SKU для Kaspi: только латиница/цифры, максимум 20 символов."""
    existing = clean_sku(item.get("kaspi_sku"))
    if item.get("kaspi_match_exists") is True and valid_kaspi_sku(existing):
        return existing, "existing_kaspi_sku"

    supplier = supplier_code(item.get("supplier_key"))
    article = clean_sku(item.get("official_article"))[:7]
    digest = stable_hash(item.get("product_key"), 8)
    sku = f"VA{supplier}{article}{digest}"[:20]
    if not valid_kaspi_sku(sku):
        sku = f"VA{supplier}{digest}"[:20]
    return sku, "generated_from_product_key"


def item_warning_flags(item: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if not text(item.get("kaspi_title")):
        warnings.append("missing_kaspi_title")
    if not text(item.get("brand")):
        warnings.append("missing_brand")
    if not text(item.get("category_key")):
        warnings.append("missing_category_key")
    if not text(item.get("kaspi_description")):
        warnings.append("missing_kaspi_description")
    if not safe_list(item.get("kaspi_images")):
        warnings.append("missing_kaspi_images")
    if not safe_dict(item.get("kaspi_attributes")):
        warnings.append("missing_kaspi_attributes")
    if int_or_zero(item.get("kaspi_price")) <= 0 and item.get("export_action") != "pause_candidate":
        warnings.append("missing_or_zero_kaspi_price")
    return warnings


def delivery_config() -> dict[str, Any]:
    """Читает безопасные настройки Kaspi delivery из config/kaspi.yml."""
    from scripts.cs_kaspi.core.yaml_io import read_yaml

    cfg = read_yaml(ROOT / "config" / "kaspi.yml")
    delivery = cfg.get("delivery", {}) if isinstance(cfg, dict) else {}
    return delivery if isinstance(delivery, dict) else {}


def delivery_value(config: dict[str, Any], key: str, default: str) -> str:
    value = text(config.get(key))
    return value or default
