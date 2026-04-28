from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.commands.refresh_official_sources import run as refresh_official_sources
from scripts.cs_kaspi.commands.import_market_worklists import run as import_market_worklists
from scripts.cs_kaspi.commands.refresh_market_data import run as refresh_market_data
from scripts.cs_kaspi.commands.validate_market_inputs import run as validate_market_inputs
from scripts.cs_kaspi.commands.refresh_kaspi_matches import run as refresh_kaspi_matches
from scripts.cs_kaspi.commands.build_master_catalog import run as build_master_catalog
from scripts.cs_kaspi.commands.build_market_template import run as build_market_template
from scripts.cs_kaspi.commands.build_market_worklist import run as build_market_worklist
from scripts.cs_kaspi.commands.build_kaspi_match_template import run as build_kaspi_match_template
from scripts.cs_kaspi.commands.build_preview import run as build_preview
from scripts.cs_kaspi.commands.build_kaspi_exports import run as build_kaspi_exports
from scripts.cs_kaspi.commands.build_kaspi_delivery import run as build_kaspi_delivery
from scripts.cs_kaspi.commands.check_project import run as check_project
from scripts.cs_kaspi.core.time_utils import now_iso


def run() -> dict[str, Any]:
    result: dict[str, Any] = {"started_at": now_iso()}
    result["official"] = refresh_official_sources()
    result["market_worklist_import"] = import_market_worklists()
    result["market"] = refresh_market_data()
    result["market_input_validation"] = validate_market_inputs()
    result["kaspi_matches"] = refresh_kaspi_matches()
    result["master_summary"] = build_master_catalog()
    result["market_template"] = build_market_template()
    result["market_worklist"] = build_market_worklist()
    result["kaspi_match_template"] = build_kaspi_match_template()
    result["preview"] = build_preview()
    result["exports"] = build_kaspi_exports()
    result["delivery"] = build_kaspi_delivery()
    result["check"] = check_project()
    result["finished_at"] = now_iso()
    return result


if __name__ == "__main__":
    run()
