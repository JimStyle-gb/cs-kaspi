from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from scripts.cs_kaspi.core.read_yaml import read_yaml
from scripts.cs_kaspi.core.time_utils import now_iso
from .utils import MODEL_SPECS_PATH, get_supplier_config


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
    return None


def _number(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"(\d+[\.,]?\d*)", text)
    if not match:
        return None
    return float(match.group(1).replace(',', '.'))


def _match_model(title: str, article: str | None, specs_model: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    title_lower = (title or '').lower()
    article_lower = (article or '').lower()
    for key, cfg in specs_model.items():
        aliases = [a.lower() for a in cfg.get('aliases', [])]
        patterns = [p.lower() for p in cfg.get('identity', {}).get('article_patterns', [])]
        if any(alias in title_lower for alias in aliases) or any(pattern in article_lower for pattern in patterns):
            return key, cfg
    return None, None


def run(parsed_products_payload: dict[str, Any]) -> dict[str, Any]:
    supplier_cfg = get_supplier_config()
    mapping = supplier_cfg.get('category_mapping', {})
    model_specs_cfg = read_yaml(MODEL_SPECS_PATH).get('models', {})
    normalized_products: list[dict[str, Any]] = []

    for product in parsed_products_payload.get('products', []):
        row = deepcopy(product)
        official = row['official']
        article = official.get('product_id')
        title = official.get('title_official', '')
        model_key, model_cfg = _match_model(title, article, model_specs_cfg)
        row['model_key'] = model_key or row.get('model_key') or official.get('slug')
        row['variant_key'] = 'wifi' if 'wifi' in (title or '').lower() or 'wifi' in (article or '').lower() else None
        supplier_category_name = row.get('supplier_category_name') or next((x for x in official.get('breadcrumbs', []) if x in mapping), None)
        row['supplier_category_name'] = supplier_category_name
        row['category_key'] = mapping.get(supplier_category_name or '', row.get('category_key'))

        specs_raw = official.get('specs_raw', {})
        normalized_specs = {
            'article': article,
            'power_w': _number(specs_raw.get('Мощность')),
            'volume_l': _number(specs_raw.get('Объем камеры')),
            'programs': int(_number(specs_raw.get('Количество программ')) or 0) or None,
            'color': _normalize_color(specs_raw.get('Цвет')),
            'control_type': specs_raw.get('Управление'),
            'temperature_range_text': specs_raw.get('Температура'),
            'timer_range_text': specs_raw.get('Время'),
            'delayed_start': specs_raw.get('Отложенный старт'),
            'weight_kg': _number(specs_raw.get('Вес аэрогриля') or specs_raw.get('Вес')),
            'package_dimensions_text': specs_raw.get('Габариты'),
            'product_dimensions_text': specs_raw.get('Размеры аэрогриля (ДхШхВ)'),
            'warranty_text': specs_raw.get('Гарантия'),
            'service_life_text': specs_raw.get('Срок службы'),
            'wifi': True if 'wifi' in (title or '').lower() or 'wifi' in (article or '').lower() else None,
        }
        package = official.get('package', {})
        raw_text = package.get('raw_text', '')
        package['recipe_book'] = 'книга рецептов' in raw_text.lower()
        acc_match = re.search(r'(\d+)\s+аксесс', raw_text.lower())
        package['accessories_count'] = int(acc_match.group(1)) if acc_match else None

        row['official']['specs'] = {k: v for k, v in normalized_specs.items() if v not in (None, '', 0)}
        row['official']['package'] = package
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

    return {
        'meta': {
            'supplier_key': 'demiand',
            'built_at': now_iso(),
            'products_count': len(normalized_products),
        },
        'products': normalized_products,
    }
