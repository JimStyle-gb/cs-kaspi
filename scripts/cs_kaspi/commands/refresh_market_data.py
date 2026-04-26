from __future__ import annotations
from scripts.cs_kaspi.core.file_paths import ensure_base_dirs, get_path
from scripts.cs_kaspi.core.write_json import write_json
from scripts.cs_kaspi.core.time_utils import now_iso

def run() -> dict:
    ensure_base_dirs()
    state={"checked_at":now_iso(),"markets":{"ozon":{"checked_products":0,"found_products":0,"errors":0},"wb":{"checked_products":0,"found_products":0,"errors":0}}}
    write_json(get_path("artifacts_state_dir") / "market_state.json", state)
    return state

if __name__ == "__main__":
    run()
