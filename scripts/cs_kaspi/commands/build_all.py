from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.commands.refresh_official_sources import run as refresh_official_sources
from scripts.cs_kaspi.commands.refresh_market_data import run as refresh_market_data
from scripts.cs_kaspi.commands.build_master_catalog import run as build_master_catalog
from scripts.cs_kaspi.commands.build_market_template import run as build_market_template
from scripts.cs_kaspi.commands.build_preview import run as build_preview
from scripts.cs_kaspi.commands.build_kaspi_exports import run as build_kaspi_exports
from scripts.cs_kaspi.commands.check_project import run as check_project
from scripts.cs_kaspi.core.time_utils import now_iso


def run() -> dict[str, Any]:
    result: dict[str, Any] = {"started_at": now_iso()}
    result["official"] = refresh_official_sources()
    result["market"] = refresh_market_data()
    result["master_summary"] = build_master_catalog()
    result["market_template"] = build_market_template()
    result["preview"] = build_preview()
    result["exports"] = build_kaspi_exports()
    result["check"] = check_project()
    result["finished_at"] = now_iso()
    return result


if __name__ == "__main__":
    run()
