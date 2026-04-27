from __future__ import annotations

from scripts.cs_kaspi.core.file_paths import ROOT
from scripts.cs_kaspi.core.read_yaml import read_yaml


def run(product: dict) -> str:
    cfg = read_yaml(ROOT / "config" / "kaspi.yml")
    store_brand = cfg.get("title_rules", {}).get("store_brand_name", "VAITAN")

    official = product.get("official", {})
    model_specs = product.get("model_specs", {}) or {}
    kaspi_identity = model_specs.get("kaspi_identity", {}) or {}

    title = official.get("title_official") or official.get("title") or product.get("product_key", "")
    custom_prefix = kaspi_identity.get("kaspi_brand") or store_brand

    return f"{custom_prefix} {title}".strip() if title else product.get("product_key", "")
