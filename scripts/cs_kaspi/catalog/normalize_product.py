from __future__ import annotations
from scripts.cs_kaspi.core.text_utils import slugify

def run(product: dict) -> dict:
    item=dict(product)
    item.setdefault("product_key", slugify("_".join(filter(None,[item.get("supplier_key"),item.get("category_key"),item.get("model_key"),item.get("variant_key")]))))
    return item
