from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.commands.refresh_official_sources import run as refresh_official_sources
from scripts.cs_kaspi.commands.discover_market_data import run as discover_market_data
from scripts.cs_kaspi.commands.refresh_market_data import run as refresh_market_data
from scripts.cs_kaspi.commands.refresh_kaspi_matches import run as refresh_kaspi_matches
from scripts.cs_kaspi.commands.build_master_catalog import run as build_master_catalog
from scripts.cs_kaspi.commands.build_preview import run as build_preview
from scripts.cs_kaspi.commands.build_kaspi_exports import run as build_kaspi_exports
from scripts.cs_kaspi.commands.build_kaspi_delivery import run as build_kaspi_delivery
from scripts.cs_kaspi.commands.check_project import run as check_project
from scripts.cs_kaspi.commands.send_telegram_report import run as send_telegram_report
from scripts.cs_kaspi.core.time_utils import now_iso


def run() -> dict[str, Any]:
    result: dict[str, Any] = {"started_at": now_iso(), "mode": "v6_2_seed_listing_only"}
    result["official"] = refresh_official_sources()
    result["market_discovery"] = discover_market_data()
    result["market"] = refresh_market_data()
    result["kaspi_matches"] = refresh_kaspi_matches()
    result["master_summary"] = build_master_catalog()
    result["preview"] = build_preview()
    result["exports"] = build_kaspi_exports()
    result["delivery"] = build_kaspi_delivery()
    result["check"] = check_project()
    result["telegram"] = send_telegram_report()
    result["finished_at"] = now_iso()
    return result


if __name__ == "__main__":
    run()
