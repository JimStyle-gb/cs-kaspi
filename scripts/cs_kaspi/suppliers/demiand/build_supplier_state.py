from __future__ import annotations

from scripts.cs_kaspi.core.time_utils import now_iso
from scripts.cs_kaspi.core.write_json import write_json
from .fetch_categories import run as fetch_categories_run
from .fetch_catalog_pages import run as fetch_catalog_pages_run
from .parse_category_pages import run as parse_category_pages_run
from .build_product_index import run as build_product_index_run
from .fetch_product_pages import run as fetch_product_pages_run
from .parse_product_pages import run as parse_product_pages_run
from .fetch_manuals import run as fetch_manuals_run
from .parse_manuals import run as parse_manuals_run
from .normalize_official import run as normalize_official_run
from .utils import supplier_state_paths


def run() -> dict:
    categories_payload = fetch_categories_run()
    catalog_payload = fetch_catalog_pages_run(categories_payload)
    parsed_catalog_payload = parse_category_pages_run(catalog_payload)
    product_index_state = build_product_index_run(parsed_catalog_payload)
    product_pages_payload = fetch_product_pages_run(product_index_state)
    parsed_products_payload = parse_product_pages_run(product_pages_payload)
    manuals_payload = fetch_manuals_run()
    parsed_manuals_payload = parse_manuals_run(manuals_payload)
    normalized_payload = normalize_official_run(parsed_products_payload)

    failed_count = product_pages_payload.get('failed_count', 0)
    official_state = {
        'checked_at': now_iso(),
        'suppliers': {
            'demiand': {
                'catalog_ok': failed_count == 0,
                'categories_found': categories_payload.get('categories_count', 0),
                'catalog_pages_fetched': catalog_payload.get('catalog_pages_count', 0),
                'products_found': product_index_state.get('meta', {}).get('products_count', 0),
                'product_pages_fetched': product_pages_payload.get('product_pages_count', 0),
                'product_pages_failed': failed_count,
                'products_parsed': parsed_products_payload.get('meta', {}).get('products_count', 0),
                'products_normalized': normalized_payload.get('meta', {}).get('products_count', 0),
                'manuals_found': len(manuals_payload.get('manuals', [])),
                'manuals_parsed': parsed_manuals_payload.get('manuals_count', 0),
                'errors': failed_count,
            }
        }
    }
    write_json(supplier_state_paths()['supplier_state'], official_state)
    return official_state['suppliers']['demiand']
