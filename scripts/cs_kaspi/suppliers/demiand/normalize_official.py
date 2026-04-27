from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from scripts.cs_kaspi.core.read_yaml import read_yaml
from scripts.cs_kaspi.core.time_utils import now_iso
from scripts.cs_kaspi.core.write_json import write_json
from .utils import MODEL_SPECS_PATH, get_supplier_config, supplier_state_paths, build_product_key


def _normalize_color(text: str | None) -> str | None:
    if not text:
        return None
    text = text.lower()
    if "чер" in text:
        return "black"
    if "бел" in text:
        return "white"
    if "сер" in text or "метал" in text:
        return "metal"
    if "беж" in text:
        return "beige"
    return None


def _number(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"(\d+[\.,]?\d*)", text)
    if not match:
        return None
    return float(match.group(1).replace(',', '.'))


def _clean_article(article: str | None) -> str | None:
    if not article:
        return None
    article = re.split(r"(?:Категори[яи]:|Метк[аи]:)", article, maxsplit=1)[0].strip()
    article = re.sub(r"\s+", " ", article).strip(" ,;-")
    return article or None


def _match_model(title: str, article: str | None, specs_model: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    title_lower = (title or '').lower()
    article_lower = (_clean_article(article) or '').lower()
    best_score = -1
    best_key: str | None = None
    best_cfg: dict[str, Any] | None = None
    for key, cfg in specs_model.items():
        aliases = [a.lower() for a in cfg.get('aliases', [])]
        patterns = [p.lower() for p in cfg.get('identity', {}).get('article_patterns', [])]
        candidates = aliases + patterns
        for candidate in candidates:
            if candidate and (candidate in title_lower or candidate in article_lower):
                score = len(candidate)
                if score > best_score:
                    best_score = score
                    best_key = key
                    best_cfg = cfg
    return best_key, best_cfg


def _guess_accessory_kind(title: str) -> str | None:
    text = (title or '').lower().replace('ё', 'е')
    patterns = [
        (r'тост', 'toast_holder'),
        (r'шампур', 'skewer_holder'),
        (r'поддон', 'oil_tray'),
        (r'решетк', 'rack'),
        (r'форма.*выпеч', 'baking_pan'),
        (r'камн', 'pizza_stone'),
        (r'щипц', 'tongs'),
        (r'вертел', 'rotisserie_spit'),
        (r'корзин', 'basket'),
        (r'против', 'tray'),
    ]
    for pattern, kind in patterns:
        if re.search(pattern, text):
            return kind
    return None


def _guess_variant(title: str, article: str | None, specs_raw: dict[str, Any]) -> str | None:
    parts: list[str] = []
    text = f"{title} {article or ''} {specs_raw.get('Цвет', '')}".lower()
    if 'wifi' in text:
        parts.append('wifi')
    color = _normalize_color(specs_raw.get('Цвет') or title or article)
    if color:
        parts.append(color)
    return '_'.join(parts) if parts else None


def _guess_model_from_title(title: str) -> str | None:
    title_lower = (title or '').lower()
    ordered = ('sanders max', 'sanders', 'tison', 'waison', 'leo', 'tarvin', 'luneo')
    for key in ordered:
        if key in title_lower:
            return key.replace(' ', '_')
    return None


def _guess_model_from_article(article: str | None) -> str | None:
    text = (_clean_article(article) or '').lower()
    mapping = {
        'dk-2400': 'sanders_max',
        'dk-2200': 'sanders',
        'dk-1416': 'tison',
        'dk-1800': 'waison',
    }
    for token, model_key in mapping.items():
        if token in text:
            return model_key
    return None


def _extract_compatibility_models(title: str, article: str | None) -> list[str]:
    text = f"{title} {article or ''}".lower()
    found: list[str] = []
    for source, target in [
        ('sanders max', 'sanders_max'),
        ('sanders', 'sanders'),
        ('tison', 'tison'),
        ('waison', 'waison'),
        ('leo', 'leo'),
        ('tarvin', 'tarvin'),
        ('luneo', 'luneo'),
    ]:
        if source in text and target not in found:
            found.append(target)
    return found


def run(parsed_products_payload: dict[str, Any]) -> dict[str, Any]:
    supplier_cfg = get_supplier_config()
    mapping = supplier_cfg.get('category_mapping', {})
    model_specs_cfg = read_yaml(MODEL_SPECS_PATH).get('models', {})
    normalized_products: list[dict[str, Any]] = []

    for product in parsed_products_payload.get('products', []):
        row = deepcopy(product)
        official = row['official']
        article = _clean_article(official.get('product_id'))
        official['product_id'] = article
        title = official.get('title_official', '')
        specs_raw = official.get('specs_raw', {})

        supplier_category_name = row.get('supplier_category_name') or next((x for x in official.get('breadcrumbs', []) if x in mapping), None)
        row['supplier_category_name'] = supplier_category_name
        row['category_key'] = mapping.get(supplier_category_name or '', row.get('category_key'))

        model_key, model_cfg = _match_model(title, article, model_specs_cfg)
        model_key = model_key or _guess_model_from_article(article) or _guess_model_from_title(title) or row.get('model_key') or official.get('slug')
        variant_key = _guess_variant(title, article, specs_raw)
        row['model_key'] = model_key
        row['variant_key'] = variant_key

        normalized_specs = {
            'article': article,
            'power_w': _number(specs_raw.get('Мощность')),
            'volume_l': _number(specs_raw.get('Объем камеры')),
            'programs': int(_number(specs_raw.get('Количество программ')) or 0) or None,
            'color': _normalize_color(specs_raw.get('Цвет') or title or article),
            'control_type': specs_raw.get('Управление'),
            'temperature_range_text': specs_raw.get('Температура'),
            'timer_range_text': specs_raw.get('Время'),
            'delayed_start': specs_raw.get('Отложенный старт'),
            'weight_kg': _number(specs_raw.get('Вес аэрогриля') or specs_raw.get('Вес')),
            'package_dimensions_text': specs_raw.get('Габариты'),
            'product_dimensions_text': specs_raw.get('Размеры аэрогриля (ДхШхВ)'),
            'warranty_text': specs_raw.get('Гарантия'),
            'service_life_text': specs_raw.get('Срок службы'),
            'wifi': True if 'wifi' in f"{title} {article or ''}".lower() else None,
        }
        package = official.get('package', {})
        raw_text = package.get('raw_text', '') or ''
        package['recipe_book'] = 'книга рецептов' in raw_text.lower()
        acc_match = re.search(r'(\d+)\s+аксесс', raw_text.lower())
        package['accessories_count'] = int(acc_match.group(1)) if acc_match else package.get('accessories_count')

        row['official']['specs'] = {k: v for k, v in normalized_specs.items() if v not in (None, '', 0)}
        row['official']['package'] = package

        if row.get('category_key') == 'air_fryer_accessories':
            row['compatibility'] = {
                'models': _extract_compatibility_models(title, article),
                'article': article,
                'accessory_kind': _guess_accessory_kind(title),
            }
            accessory_base = article or row['compatibility']['accessory_kind'] or official.get('slug') or title
            row['product_key'] = build_product_key(
                row.get('category_key') or 'product',
                accessory_base,
                model_key=None,
                variant_key=None,
                article=article,
            )
        else:
            row['product_key'] = build_product_key(
                row.get('category_key') or 'product',
                official.get('slug') or title,
                model_key=model_key,
                variant_key=variant_key,
                article=article,
            )

        row['model_specs'] = {
            'exists': bool(model_cfg),
            'spec_file': str(MODEL_SPECS_PATH),
            'canonical_model_name': model_cfg.get('canonical_model_name') if model_cfg else None,
            'title_template_key': model_cfg.get('kaspi_identity', {}).get('group_key') if model_cfg else None,
            'specs_override': model_cfg.get('known_specs', {}) if model_cfg else {},
            'content_blocks': model_cfg.get('content_defaults', {}) if model_cfg else {},
        }
        row['normalized_at'] = now_iso()
        normalized_products.append(row)

    state = {
        'meta': {
            'supplier_key': 'demiand',
            'built_at': now_iso(),
            'products_count': len(normalized_products),
        },
        'products': normalized_products,
    }
    write_json(supplier_state_paths()['official_products'], state)
    return state
