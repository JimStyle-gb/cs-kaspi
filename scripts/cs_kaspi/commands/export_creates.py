from __future__ import annotations
from scripts.cs_kaspi.core.file_paths import ensure_base_dirs, get_path
from scripts.cs_kaspi.core.read_json import read_json
from scripts.cs_kaspi.core.write_json import write_json
from scripts.cs_kaspi.kaspi.build_create_plan import run as build_plan
from scripts.cs_kaspi.kaspi.build_create_payload import run as build_payload

def run() -> dict:
    ensure_base_dirs()
    catalog=read_json(get_path("artifacts_state_dir") / "master_catalog.json", default={"products":[]})
    plan=build_plan(catalog.get("products",[]))
    payload=build_payload(plan)
    write_json(get_path("artifacts_state_dir") / "create_plan.json", plan)
    write_json(get_path("artifacts_exports_dir") / "create_payload.json", payload)
    return payload

if __name__ == "__main__":
    run()
