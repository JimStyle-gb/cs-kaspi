from __future__ import annotations

from scripts.cs_kaspi.core.text_utils import clean_html_text, normalize_spaces


def _line(label: str, value) -> str | None:
    if value in (None, "", [], {}):
        return None
    return f"<li><b>{label}:</b> {clean_html_text(str(value))}</li>"


def run(product: dict) -> str:
    official = product.get("official", {})
    specs = official.get("specs", {}) or {}
    title = clean_html_text(product.get("kaspi_policy", {}).get("kaspi_title") or official.get("title_official") or "Товар")
    short = clean_html_text(official.get("short_description") or official.get("description_official") or "")

    items = [
        _line("Бренд", product.get("brand")),
        _line("Артикул", official.get("product_id")),
        _line("Мощность", f"{specs.get('power_w')} Вт" if specs.get("power_w") else None),
        _line("Объем", f"{specs.get('volume_l')} л" if specs.get("volume_l") else None),
        _line("Количество программ", specs.get("programs")),
        _line("Цвет", specs.get("color")),
        _line("Управление", specs.get("control_type")),
        _line("Гарантия", specs.get("warranty_text")),
    ]
    items = [x for x in items if x]
    specs_html = "" if not items else "<h3>Характеристики</h3><ul>" + "".join(items) + "</ul>"

    parts = [f"<h3>{title}</h3>"]
    if short:
        parts.append(f"<p>{short}</p>")
    parts.append(specs_html)
    parts.append("<p>Карточка подготовлена на основе официального источника поставщика. Цена и наличие для Kaspi рассчитываются отдельным коммерческим слоем.</p>")
    return normalize_spaces("".join(parts))
