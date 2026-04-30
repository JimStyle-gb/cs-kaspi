from __future__ import annotations

from typing import Any

from scripts.cs_kaspi.markets.discovery.build_market_discovery import run as build_market_discovery


def run() -> dict[str, Any]:
    return build_market_discovery()


if __name__ == "__main__":
    run()
