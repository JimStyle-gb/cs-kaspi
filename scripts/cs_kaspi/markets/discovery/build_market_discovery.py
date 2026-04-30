from __future__ import annotations

from typing import Any

from .build_profiles import run as build_profiles
from .choose_best_offers import run as choose_best_offers
from .listing_browser import fetch_seed
from .match_listings import score_listing_cards, split_by_status
from .parse_listing import normalize_cards
from .seed_config import discovery_cfg, seeds
from .write_outputs import run as write_outputs


def _enabled() -> bool:
    return discovery_cfg().get("enabled", True) is not False


def run() -> dict[str, Any]:
    profiles = build_profiles()
    seed_rows = seeds()
    raw_cards: list[dict[str, Any]] = []
    source_reports: list[dict[str, Any]] = []

    if _enabled():
        for seed in seed_rows:
            cards, report = fetch_seed(seed)
            raw_cards.extend(cards)
            source_reports.append(report)
    else:
        source_reports.append({"source": "market_discovery", "status": "disabled", "errors": ["disabled_by_config"]})

    listings = normalize_cards(raw_cards)
    scored = score_listing_cards(listings, profiles)
    split = split_by_status(scored)
    best = choose_best_offers(split["accepted"], split["review_needed"], split["rejected"])

    return write_outputs(
        profiles=profiles,
        seeds=seed_rows,
        raw_cards=raw_cards,
        listings=listings,
        scored_candidates=scored,
        best_result=best,
        source_reports=source_reports,
    )
