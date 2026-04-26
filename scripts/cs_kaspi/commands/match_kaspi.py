from __future__ import annotations
from scripts.cs_kaspi.core.file_paths import ensure_base_dirs, get_path
from scripts.cs_kaspi.core.read_json import read_json
from scripts.cs_kaspi.core.write_json import write_json
from scripts.cs_kaspi.kaspi.read_existing import run as read_existing
from scripts.cs_kaspi.kaspi.match_products import run as match_products

def run() -> dict:
    ensure_base_dirs()
    catalog=read_json(get_path("artifacts_state_dir") / "master_catalog.json", default={"products":[]})
    existing=read_existing()
    matched=match_products(catalog.get("products",[]), existing)
    result={"checked_at":None,"matched":sum(1 for p in matched if p.get("kaspi_match",{}).get("exists_in_kaspi")),"new_products":sum(1 for p in matched if not p.get("kaspi_match",{}).get("exists_in_kaspi")),"unresolved":0,"paused_candidates":sum(1 for p in matched if p.get("status",{}).get("action_status")=="pause")}
    write_json(get_path("artifacts_state_dir") / "kaspi_match.json", result)
    return result

if __name__ == "__main__":
    run()
