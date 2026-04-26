from __future__ import annotations
from scripts.cs_kaspi.core.file_paths import ensure_base_dirs, get_path
from scripts.cs_kaspi.core.read_json import read_json
from scripts.cs_kaspi.core.write_json import write_json
from scripts.cs_kaspi.core.time_utils import now_iso

def run() -> dict:
    ensure_base_dirs()
    catalog=read_json(get_path("artifacts_state_dir") / "master_catalog.json", default={"products":[]})
    products=catalog.get("products",[])
    report={"built_at":now_iso(),"totals":{"products":len(products),"official_active":sum(1 for p in products if p.get("official",{}).get("exists")),"market_found":sum(1 for p in products if p.get("market",{}).get("sellable")),"kaspi_ready":sum(1 for p in products if p.get("status",{}).get("kaspi_status")=="ready"),"kaspi_active":sum(1 for p in products if p.get("status",{}).get("kaspi_status")=="active"),"kaspi_paused":sum(1 for p in products if p.get("status",{}).get("kaspi_status")=="paused"),"needs_review":sum(1 for p in products if p.get("status",{}).get("needs_review")),"blocked":sum(1 for p in products if p.get("status",{}).get("kaspi_status")=="blocked")},"actions":{"create":sum(1 for p in products if p.get("status",{}).get("action_status")=="create"),"update":sum(1 for p in products if p.get("status",{}).get("action_status")=="update"),"pause":sum(1 for p in products if p.get("status",{}).get("action_status")=="pause"),"skip":sum(1 for p in products if p.get("status",{}).get("action_status")=="skip")}}
    review={"built_at":now_iso(),"count":0,"products":[]}
    write_json(get_path("artifacts_reports_dir") / "check_project_report.json", report)
    write_json(get_path("artifacts_reports_dir") / "review_report.json", review)
    return report

if __name__ == "__main__":
    run()
