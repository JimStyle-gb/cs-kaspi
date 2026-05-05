from __future__ import annotations

import re
from typing import Any


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _split_values(value: Any) -> list[str]:
    raw = _norm(value)
    if not raw:
        return []
    return [v.strip() for v in re.split(r"[,;]", raw) if v.strip()]


def _allowed(template: dict[str, Any], name_ru: str) -> set[str]:
    return {str(v).strip() for v in (template.get("value_lists", {}) or {}).get(name_ru, []) or [] if str(v).strip()}


def validate_row(row: dict[str, Any], template: dict[str, Any]) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    name_by_code = {field.get("code"): field.get("name_ru") for field in template.get("fields", [])}

    for field in template.get("fields", []):
        code = str(field.get("code") or "")
        name = str(field.get("name_ru") or code)
        value = row.get(code)
        if field.get("required") and _norm(value) == "":
            errors.append(f"missing_required:{name}")
            continue
        if _norm(value) == "":
            continue

        field_type = str(field.get("type") or "")
        allowed = _allowed(template, name)
        if field_type in {"single_list", "multi_list"} and allowed:
            values = _split_values(value) if field_type == "multi_list" else [_norm(value)]
            invalid = [v for v in values if v not in allowed]
            if invalid:
                errors.append(f"invalid_value:{name}:{'|'.join(invalid[:5])}")
        elif field_type == "boolean":
            if _norm(value).upper() not in {"TRUE", "FALSE", "ДА", "НЕТ", "1", "0"}:
                errors.append(f"invalid_boolean:{name}:{value}")
        elif field_type == "number":
            try:
                float(str(value).replace(",", "."))
            except Exception:
                errors.append(f"invalid_number:{name}:{value}")

    desc_code = next((c for c, n in name_by_code.items() if str(n).startswith("Описание")), "")
    if desc_code:
        desc = _norm(row.get(desc_code))
        if "<" in desc or ">" in desc:
            errors.append("description_contains_html")
        if desc and len(desc) < 100:
            errors.append("description_too_short")
        if len(desc) > 7000:
            errors.append("description_too_long")

    sku = _norm(row.get("merchant_sku"))
    if len(sku) > 64:
        warnings.append("merchant_sku_longer_than_64")
    return {"errors": errors, "warnings": warnings}
