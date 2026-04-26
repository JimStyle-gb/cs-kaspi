from __future__ import annotations
from scripts.cs_kaspi.core.read_yaml import read_yaml
from scripts.cs_kaspi.core.file_paths import ROOT

def run(product: dict) -> int:
    cfg=read_yaml(ROOT/"config"/"kaspi.yml")
    return int(cfg.get("lead_time_rules",{}).get("default_days",1))
