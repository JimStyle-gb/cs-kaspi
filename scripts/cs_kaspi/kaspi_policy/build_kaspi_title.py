from __future__ import annotations
from scripts.cs_kaspi.core.read_yaml import read_yaml
from scripts.cs_kaspi.core.file_paths import ROOT

def run(product: dict) -> str:
    cfg = read_yaml(ROOT / "config" / "kaspi.yml")
    store_brand = cfg.get("title_rules", {}).get("store_brand_name", "VAITAN")
    official_title = product.get("official", {}).get("title", "")
    return f"{store_brand} {official_title}".strip() if official_title else product.get("product_key","")
