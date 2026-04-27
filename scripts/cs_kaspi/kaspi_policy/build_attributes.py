from __future__ import annotations


def _add(attrs: dict[str, str], key: str, value) -> None:
    if value not in (None, "", [], {}):
        attrs[key] = str(value)


def run(product: dict) -> dict[str, str]:
    official = product.get("official", {})
    specs = official.get("specs", {}) or {}
    attrs: dict[str, str] = {}
    _add(attrs, "Бренд", product.get("brand"))
    _add(attrs, "Артикул", official.get("product_id"))
    _add(attrs, "Категория", product.get("supplier_category_name") or product.get("category_key"))
    _add(attrs, "Модель", product.get("model_key"))
    _add(attrs, "Цвет", specs.get("color"))
    _add(attrs, "Мощность, Вт", specs.get("power_w"))
    _add(attrs, "Объем, л", specs.get("volume_l"))
    _add(attrs, "Количество программ", specs.get("programs"))
    _add(attrs, "Управление", specs.get("control_type"))
    _add(attrs, "Температура", specs.get("temperature_range_text"))
    _add(attrs, "Таймер", specs.get("timer_range_text"))
    _add(attrs, "Вес, кг", specs.get("weight_kg"))
    _add(attrs, "Гарантия", specs.get("warranty_text"))
    compatibility = product.get("compatibility", {}) or {}
    if compatibility.get("models"):
        _add(attrs, "Совместимые модели", ", ".join(compatibility["models"]))
    if compatibility.get("accessory_kind"):
        _add(attrs, "Тип аксессуара", compatibility["accessory_kind"])
    return attrs
