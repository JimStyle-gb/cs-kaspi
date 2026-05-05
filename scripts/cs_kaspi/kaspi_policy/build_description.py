from __future__ import annotations

from scripts.cs_kaspi.core.text_utils import clean_html_text, normalize_spaces


def _line(label: str, value) -> str | None:
    if value in (None, "", [], {}):
        return None
    return f"<li><b>{label}:</b> {clean_html_text(str(value))}</li>"


def run(product: dict) -> str:
    official = product.get("official", {}) or {}
    specs = official.get("specs", {}) or {}
    market = product.get("market", {}) or {}
    title = clean_html_text(product.get("kaspi_policy", {}).get("kaspi_title") or market.get("market_title") or official.get("title_official") or "Товар")
    short = clean_html_text(official.get("short_description") or official.get("description_official") or "")
    is_market_only = product.get("is_market_only") is True or official.get("status") == "market_only_wb"

    items = [
        _line("Бренд", product.get("brand")),
        _line("Артикул", official.get("product_id") if not is_market_only else None),
        _line("WB товар", market.get("market_title")),
        _line("Рыночная комплектация", market.get("market_bundle")),
        _line("Ссылка WB", market.get("market_url")),
        _line("Мощность", f"{specs.get('power_w')} Вт" if specs.get("power_w") else None),
        _line("Объем", f"{specs.get('volume_l')} л" if specs.get("volume_l") else None),
        _line("Количество программ", specs.get("programs")),
        _line("Цвет", market.get("market_color") or specs.get("color")),
        _line("Управление", specs.get("control_type")),
        _line("Гарантия", specs.get("warranty_text")),
    ]
    items = [x for x in items if x]
    specs_html = "" if not items else "<h3>Характеристики</h3><ul>" + "".join(items) + "</ul>"

    parts = [f"<h3>{title}</h3>"]
    if short:
        parts.append(f"<p>{short}</p>")
    elif market.get("market_title"):
        parts.append(f"<p>{clean_html_text(str(market.get('market_title')))} — товар бренда DEMIAND, найденный в подтверждённой выдаче WB по указанной seed-ссылке.</p>")
    parts.append(specs_html)
    if is_market_only:
        parts.append("<p>Official-карточка не использована как жёсткий фильтр: товар взят из WB как продаваемый вариант DEMIAND. После настройки финальных категорий Kaspi описание можно дополнительно усилить вручную или official-данными, если появится точное совпадение.</p>")
    elif market.get("market_bundle") or market.get("market_title"):
        parts.append("<p>Комплектация и рыночный вариант берутся из подтверждённой карточки WB, а технические характеристики — из официального источника поставщика.</p>")
    else:
        parts.append("<p>Карточка подготовлена на основе официального источника поставщика. Цена и наличие для Kaspi рассчитываются отдельным коммерческим слоем.</p>")
    return normalize_spaces("".join(parts))
