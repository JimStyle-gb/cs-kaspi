from __future__ import annotations
from scripts.cs_kaspi.core.read_yaml import read_yaml
from scripts.cs_kaspi.core.file_paths import ROOT

def run(product: dict) -> int:
    cfg=read_yaml(ROOT/"config"/"kaspi.yml")
    return int(cfg.get("stock_rules",{}).get("default_stock_if_sellable",5)) if product.get("market",{}).get("sellable") else 0
