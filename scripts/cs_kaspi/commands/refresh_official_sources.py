from __future__ import annotations

from scripts.cs_kaspi.core.file_paths import ensure_base_dirs, get_path
from scripts.cs_kaspi.core.write_json import write_json
from scripts.cs_kaspi.core.time_utils import now_iso
from scripts.cs_kaspi.suppliers.demiand.build_supplier_state import run as demiand_state


def run() -> dict:
    ensure_base_dirs()
    demiand = demiand_state()
    state = {"checked_at": now_iso(), "suppliers": {"demiand": demiand}}
    write_json(get_path("artifacts_state_dir") / "official_state.json", state)
    return state


if __name__ == "__main__":
    run()
