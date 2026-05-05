from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .common import (
    allowed_values,
    base_row,
    contains_any,
    first_number,
    load_template,
    normalize_color,
    number,
    put,
    template_key_for_category,
    text_blob,
)


def _air_fryer_row(product: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    row = base_row(product, template)
    official = product.get("official", {}) or {}
    market = product.get("market", {}) or {}
    specs = official.get("specs", {}) or {}
    blob = text_blob(product)

    volume = specs.get("volume_l") or first_number(blob, suffixes=("л", "l"))
    programs = specs.get("programs") or first_number(blob, suffixes=("программ", "программы", "programs"))
    control = str(specs.get("control_type") or "").lower()
    smartphone = bool(specs.get("wifi")) or contains_any(blob + " " + control, ["wi-fi", "wifi", "вай-фай", "телефон", "смартфон"])
    two_ten = contains_any(blob, ["2 тэн", "2 тен", "два тэн", "два тен", "двумя тэн", "двумя тен"])
    two_bowls = contains_any(blob, ["две чаш", "двумя чаш", "2 чаш"])

    put(row, template, "Мощность", number(specs.get("power_w")))
    put(row, template, "Материал корпуса", "пластик")
    put(row, template, "Материал рабочей поверхности", "антипригарное покрытие" if "керамическ" not in blob else "керамика")
    put(row, template, "Управление", "сенсорное" if ("сенсор" in control or smartphone) else "электронное")
    put(row, template, "Модель", specs.get("article") or product.get("model_key"))
    components = ["инструкция"]
    if contains_any(blob, ["решет", "решёт", "гриль"]):
        components.append("решетка")
    if contains_any(blob, ["чаша", "корзин"]):
        components.append("съемная корзина")
    put(row, template, "Комплектация", ", ".join(dict.fromkeys(components)))
    put(row, template, "Объем чаши", number(volume))
    put(row, template, "Количество чаш", "2 шт" if two_bowls else "1 шт")
    put(row, template, "Количество автоматических программ", number(programs))
    put(row, template, "Минимальная температура нагрева", 80)
    put(row, template, "Максимальная температура нагрева", 200)
    put(row, template, "Нагревательный элемент", "ТЭН")
    put(row, template, "Количество нагревательных элементов", "2 шт" if two_ten else "1 шт")
    put(row, template, "Особенности", "управление через смартфон" if smartphone else "антипригарное покрытие чаши")
    put(row, template, "Размеры", specs.get("product_dimensions_text") or specs.get("package_dimensions_text"))
    put(row, template, "Серийная модель(для объединения по цвету)", product.get("model_key") or specs.get("article"))
    put(row, template, "Антипригарное покрытие чаши", True)
    put(row, template, "Управление со смартфона", smartphone)
    put(row, template, "Регулировка времени приготовления", True)
    put(row, template, "Регулировка температуры приготовления", True)
    put(row, template, "Таймер", True)
    put(row, template, "Максимальное время установки таймера", 1)
    put(row, template, "Отсрочка старта", bool(specs.get("delayed_start")))
    put(row, template, "Цвет", normalize_color(market.get("market_color") or specs.get("color")))
    put(row, template, "Страна производства", "Китай")
    return row


def _blender_row(product: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    row = base_row(product, template)
    official = product.get("official", {}) or {}
    market = product.get("market", {}) or {}
    specs = official.get("specs", {}) or {}
    blob = text_blob(product)
    power = specs.get("power_w") or first_number(str(specs.get("article") or product.get("model_key") or "")) or 1200
    control = str(specs.get("control_type") or "").lower()
    put(row, template, "Тип", "стационарный")
    put(row, template, "Беспроводной", False)
    put(row, template, "Мощность", number(power))
    put(row, template, "Управление", "сенсорное" if "сенсор" in control or "сенсор" in blob else "электронное")
    put(row, template, "Количество скоростей", number(specs.get("programs") or 8))
    put(row, template, "Плавная регулировка скорости", True)
    put(row, template, "Модель", specs.get("article") or product.get("model_key"))
    put(row, template, "Серийная модель (для объединения)", product.get("model_key") or specs.get("article"))
    put(row, template, "Дополнительные режимы", "измельчение, смешивание, смузи")
    put(row, template, "Вакуумный насос", False)
    put(row, template, "Венчик для взбивания", False)
    put(row, template, "Дорожная бутылка", False)
    put(row, template, "Измельчитель", True)
    put(row, template, "Мерный стакан", False)
    put(row, template, "Мельничка", False)
    put(row, template, "Материал корпуса", "пластик")
    put(row, template, "Материал кувшина", "стекло")
    put(row, template, "Материал ножей", "нержавеющая сталь")
    put(row, template, "Размеры (ШxВxГ)", specs.get("product_dimensions_text") or specs.get("package_dimensions_text"))
    put(row, template, "Цвет", normalize_color(market.get("market_color") or specs.get("color")))
    put(row, template, "Страна производства", "Китай")
    return row


def _accessory_type(blob: str) -> str:
    if contains_any(blob, ["шампур"]):
        return "шампуры"
    if contains_any(blob, ["решет", "решёт"]):
        return "решетка"
    if contains_any(blob, ["корзин", "чаша"]):
        return "чаша"
    if contains_any(blob, ["стакан"]):
        return "стакан"
    if contains_any(blob, ["поддон", "вкладыш", "пергамент"]):
        return "лоток"
    if contains_any(blob, ["держател"]):
        return "держатель втулки"
    return "насадка"


def _accessory_material(blob: str) -> str:
    if contains_any(blob, ["силикон"]):
        return "силикон"
    if contains_any(blob, ["бумаж", "пергамент"]):
        return "бумага"
    if contains_any(blob, ["нержав", "сталь", "металл", "шампур", "решет", "решёт"]):
        return "нерж. сталь"
    if contains_any(blob, ["стекл"]):
        return "стекло"
    return "пластик"


def _accessory_row(product: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    row = base_row(product, template)
    official = product.get("official", {}) or {}
    market = product.get("market", {}) or {}
    specs = official.get("specs", {}) or {}
    blob = text_blob(product)
    purpose = "для кофеварки" if product.get("category_key") == "coffee_maker_accessories" or "кофевар" in blob else "для аэрогриля"
    put(row, template, "Назначение", purpose)
    put(row, template, "Тип", _accessory_type(blob))
    put(row, template, "Материал", _accessory_material(blob))
    put(row, template, "Размеры", specs.get("product_dimensions_text") or specs.get("package_dimensions_text"))
    put(row, template, "Совместимая модель", product.get("model_key"))
    qty = first_number(blob, suffixes=("штук", "шт"))
    put(row, template, "Количество", int(qty) if qty else 1)
    put(row, template, "Цвет", normalize_color(market.get("market_color") or specs.get("color")) or "серый")
    put(row, template, "Страна производства", "Китай")
    return row


def _oven_row(product: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    row = base_row(product, template)
    official = product.get("official", {}) or {}
    market = product.get("market", {}) or {}
    specs = official.get("specs", {}) or {}
    blob = text_blob(product)
    volume = specs.get("volume_l") or first_number(blob, suffixes=("л", "l"))
    put(row, template, "Объем духовки", number(volume))
    put(row, template, "Мощность духовки", number(specs.get("power_w")))
    put(row, template, "Количество режимов работы", str(number(specs.get("programs") or 6)))
    put(row, template, "Количество конфорок", "отсутствует")
    put(row, template, "Минимальная температура", 80)
    put(row, template, "Максимальная температура", 230)
    put(row, template, "Конвекция", True)
    put(row, template, "Гриль", True)
    put(row, template, "Вертел", False)
    put(row, template, "Внутреннее покрытие", "эмаль")
    put(row, template, "Особенности", "таймер обратного отсчета, внутренняя подсветка")
    put(row, template, "Габариты", specs.get("product_dimensions_text") or specs.get("package_dimensions_text"))
    put(row, template, "Комплектация", "противень, решетка, инструкция")
    put(row, template, "Модель", specs.get("article") or product.get("model_key"))
    put(row, template, "Цвет", normalize_color(market.get("market_color") or specs.get("color")))
    put(row, template, "Страна производства", "Китай")
    return row


def build_row(product: dict[str, Any]) -> dict[str, Any]:
    template_key = template_key_for_category(product.get("category_key"))
    template = load_template(template_key)
    if not template:
        return {"template_key": template_key, "row": {}, "errors": ["missing_template"]}
    if template_key == "air_fryers":
        row = _air_fryer_row(product, template)
    elif template_key == "blenders":
        row = _blender_row(product, template)
    elif template_key == "accessories_small_kitchen":
        row = _accessory_row(product, template)
    elif template_key == "tabletop_ovens":
        row = _oven_row(product, template)
    else:
        return {"template_key": template_key, "row": {}, "errors": ["unsupported_template"]}
    return {"template_key": template_key, "template": template, "row": row, "errors": []}


def build_rows(products: list[dict[str, Any]]) -> dict[str, Any]:
    from .validate_rows import validate_row

    ready: dict[str, list[dict[str, Any]]] = defaultdict(list)
    blocked: list[dict[str, Any]] = []
    rows_all: list[dict[str, Any]] = []
    counters = Counter()

    for product in products:
        status = product.get("status", {}) or {}
        kaspi = product.get("kaspi_policy", {}) or {}
        if status.get("action_status") != "ready_for_create_or_update" or kaspi.get("kaspi_available") is not True:
            continue
        built = build_row(product)
        template_key = built.get("template_key") or "missing"
        row = built.get("row") or {}
        template = built.get("template") or load_template(template_key)
        errors = list(built.get("errors") or [])
        warnings: list[str] = []
        if template and row:
            result = validate_row(row, template)
            errors.extend(result.get("errors", []))
            warnings.extend(result.get("warnings", []))
        payload = {
            "product_key": product.get("product_key"),
            "category_key": product.get("category_key"),
            "template_key": template_key,
            "kaspi_title": kaspi.get("kaspi_title"),
            "kaspi_price": kaspi.get("kaspi_price"),
            "market_price": kaspi.get("market_price"),
            "market_url": (product.get("market", {}) or {}).get("market_url"),
            "row": row,
            "errors": errors,
            "warnings": warnings,
        }
        rows_all.append(payload)
        if errors:
            counters["blocked"] += 1
            blocked.append(payload)
        else:
            counters["ready"] += 1
            ready[template_key].append(payload)
        counters[template_key] += 1

    return {
        "meta": {
            "commercial_candidates": sum(counters[k] for k in counters if k not in {"ready", "blocked"}),
            "template_ready": counters["ready"],
            "template_blocked": counters["blocked"],
            "by_template": {k: v for k, v in counters.items() if k not in {"ready", "blocked"}},
        },
        "ready_by_template": dict(ready),
        "blocked": blocked,
        "rows": rows_all,
    }
