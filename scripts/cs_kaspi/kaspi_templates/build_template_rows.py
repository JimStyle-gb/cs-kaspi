from __future__ import annotations

from collections import Counter, defaultdict
import re
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


def _temperature_bounds(specs: dict[str, Any], blob: str, *, default_min: int, default_max: int) -> tuple[Any, Any]:
    """Берёт температуру из specs/range без угадывания из случайных чисел."""
    min_value = specs.get("temperature_min_c") or specs.get("min_temperature_c")
    max_value = specs.get("temperature_max_c") or specs.get("max_temperature_c")
    range_text = str(specs.get("temperature_range_text") or "")
    if (not min_value or not max_value) and range_text:
        nums = [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[\.,]\d+)?", range_text)]
        if len(nums) >= 2:
            min_value = min_value or nums[0]
            max_value = max_value or nums[1]
    return number(min_value or default_min), number(max_value or default_max)


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
    min_temp, max_temp = _temperature_bounds(specs, blob, default_min=80, default_max=200)
    put(row, template, "Минимальная температура нагрева", min_temp)
    put(row, template, "Максимальная температура нагрева", max_temp)
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
    min_temp, max_temp = _temperature_bounds(specs, blob, default_min=80, default_max=230)
    put(row, template, "Минимальная температура", min_temp)
    put(row, template, "Максимальная температура", max_temp)
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



def _number_from_ml_or_l(blob: str, marker: str) -> Any:
    """Извлекает объём резервуара из текста: 1,6 л или 1600 мл."""
    safe_marker = re.escape(marker)
    m_l = re.search(rf"{safe_marker}[^.;:]*?(\d+(?:[\.,]\d+)?)\s*л", blob, flags=re.IGNORECASE)
    if m_l:
        return number(m_l.group(1).replace(",", "."))
    m_ml = re.search(rf"{safe_marker}[^.;:]*?(\d+(?:[\.,]\d+)?)\s*мл", blob, flags=re.IGNORECASE)
    if m_ml:
        try:
            return number(float(m_ml.group(1).replace(",", ".")) / 1000)
        except Exception:
            return ""
    return ""


def _coffee_machine_row(product: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    row = base_row(product, template)
    official = product.get("official", {}) or {}
    market = product.get("market", {}) or {}
    specs = official.get("specs", {}) or {}
    blob = text_blob(product)

    coffee_type = specs.get("coffee_machine_type") or ("кофеварка" if "кофевар" in blob else "кофемашина")
    coffee_view = specs.get("coffee_machine_view")
    if not coffee_view:
        if "рожков" in blob:
            coffee_view = "рожковая"
        elif "капсуль" in blob:
            coffee_view = "капсульная"
        elif "капель" in blob:
            coffee_view = "капельная"
    used_coffee = specs.get("coffee_used")
    if not used_coffee:
        used = []
        if contains_any(blob, ["молот"]):
            used.append("молотый")
        if contains_any(blob, ["чалд"]):
            used.append("чалды")
        if contains_any(blob, ["капсул", "nespresso"]):
            used.append("капсулы")
        used_coffee = ", ".join(dict.fromkeys(used))
    heater_type = specs.get("heater_type") or ("термоблок" if contains_any(blob, ["эспрессо", "помпа", "рожков"]) else "")
    pressure_bar = specs.get("pressure_bar") or first_number(blob, suffixes=("бар",))
    water_tank_l = specs.get("water_tank_l") or _number_from_ml_or_l(blob, "резервуар для воды")
    control = str(specs.get("control_type") or "").lower()
    has_cappuccinator = bool(specs.get("cappuccinator")) or contains_any(blob, ["капучинатор", "капучино", "латте", "молочной пен"])
    has_display = specs.get("display") or ("с подсветкой" if contains_any(blob, ["led-дисплей", "led дисплей", "жк-дисплей"]) else ("есть" if "дисплей" in blob else "нет"))
    case_material = specs.get("case_material") or "металл/пластик"

    put(row, template, "Тип", coffee_type)
    put(row, template, "Вид", coffee_view)
    put(row, template, "Приготовление эспрессо", "автоматическое" if "автомат" in blob else "полуавтоматическое")
    put(row, template, "Количество групп", "1")
    put(row, template, "Используемый кофе", used_coffee)
    put(row, template, "Материал рожка", "металл")
    put(row, template, "Тип нагревателя", heater_type)
    put(row, template, "Раздельные бойлеры", False)
    put(row, template, "Мощность", number(specs.get("power_w")))
    put(row, template, "Объем резервуара для воды", water_tank_l)
    put(row, template, "Максимальное давление", number(pressure_bar))
    put(row, template, "Манометр", False)
    put(row, template, "Настройки", specs.get("settings") or "регулировка температуры кофе, контроль крепости кофе")
    put(row, template, "Регулировка жесткости воды", False)
    put(row, template, "Автоматическая декальцинация", bool(specs.get("auto_decalcification")) or contains_any(blob, ["очистка от накипи", "декальцинац"]))
    put(row, template, "Возможность приготовления капучино", has_cappuccinator)
    put(row, template, "Приготовление капучино", specs.get("cappuccino_preparation") or ("автоматическое" if has_cappuccinator else "отсутствует"))
    put(row, template, "Модель", specs.get("article") or product.get("model_key"))
    put(row, template, "Отключение", "автоотключение" if contains_any(blob, ["автоотключ"]) else "")
    put(row, template, "Материал корпуса", case_material)
    put(row, template, "Индикаторы", specs.get("indicators") or "режима работы, уровня воды")
    put(row, template, "Размеры (ШxВxГ)", specs.get("product_dimensions_text") or specs.get("package_dimensions_text"))
    put(row, template, "Вес", number(specs.get("weight_kg")))
    put(row, template, "Дополнительная информация", "автоматический капучинатор" if has_cappuccinator else "")
    put(row, template, "Комплектация", specs.get("complete_set") or "рожок, фильтр, резервуар для молока, инструкция")
    put(row, template, "Возможности", "без дополнительных функций")
    put(row, template, "Кофемолка", bool(specs.get("coffee_grinder")))
    put(row, template, "Фильтр", specs.get("filter_type") or "многоразовый")
    put(row, template, "Противокапельная система", bool(specs.get("drip_stop")))
    put(row, template, "Одновременное приготовление двух чашек", contains_any(blob, ["двух порц", "2 эспрессо", "двойной порц"]))
    put(row, template, "Подогрев чашек", bool(specs.get("cups_heating")) or contains_any(blob, ["подогрев чаш"] ))
    put(row, template, "Особенности корпуса", specs.get("case_features") or "съемный лоток для сбора капель")
    put(row, template, "Подсветка", False)
    put(row, template, "Дисплей", has_display)
    put(row, template, "Подача горячей воды", contains_any(blob, ["американо", "горячей воды"]))
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
    elif template_key == "coffee_machines":
        row = _coffee_machine_row(product, template)
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
