from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.json_io import write_json
from scripts.cs_kaspi.core.paths import path_from_config
from scripts.cs_kaspi.core.time_utils import now_iso

REVIEW_HEADERS = [
    "source", "seed_key", "market_title", "market_url", "market_price", "market_available",
    "market_stock", "eta_text", "lead_time_days", "brand", "model_key", "category_key",
    "base_product_key", "market_color", "market_bundle", "variant_signature", "match_confidence", "reason",
]


def _write_review_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=REVIEW_HEADERS)
        writer.writeheader()
        for row in rows:
            item = {key: row.get(key, "") for key in REVIEW_HEADERS}
            if not item.get("reason"):
                if not row.get("market_price"):
                    item["reason"] = "missing_price_or_not_visible_in_listing"
                elif int(row.get("match_confidence") or 0) < 70:
                    item["reason"] = "low_model_confidence"
                else:
                    item["reason"] = "needs_manual_review"
            writer.writerow(item)


def _write_seed_report(path: Path, reports: list[dict[str, Any]]) -> None:
    lines = ["CS-Kaspi v6 seed listing report", ""]
    for report in reports:
        errors = report.get("errors") or []
        warnings = report.get("warnings") or []
        lines.append(f"seed: {report.get('seed_key')}")
        lines.append(f"  source: {report.get('source')}")
        lines.append(f"  status: {report.get('status')}")
        lines.append(f"  cards_unique_url: {report.get('cards_unique_url')}")
        lines.append(f"  scroll_rounds: {report.get('scroll_rounds')}")
        if warnings:
            lines.append(f"  warnings: {' | '.join(map(str, warnings))}")
        if errors:
            lines.append(f"  errors: {' | '.join(map(str, errors))}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result.get("summary", {}) or {}
    lines = [
        "CS-Kaspi v6 market discovery report",
        f"built_at: {result.get('built_at')}",
        f"mode: {result.get('mode')}",
        f"official_profiles: {summary.get('profiles', 0)}",
        f"seed_urls: {summary.get('seed_urls', 0)}",
        f"raw_cards: {summary.get('raw_cards', 0)}",
        f"listing_cards: {summary.get('listing_cards', 0)}",
        f"scored_candidates: {summary.get('scored_candidates', 0)}",
        f"auto_best_offer_records: {summary.get('auto_best_offer_records', 0)}",
        f"duplicates_collapsed: {summary.get('duplicates_collapsed', 0)}",
        f"review_needed: {summary.get('review_needed', 0)}",
        f"rejected: {summary.get('rejected', 0)}",
        f"seed_errors: {summary.get('seed_errors', 0)}",
        f"seed_warnings: {summary.get('seed_warnings', 0)}",
        "",
        "Rules:",
        "- Ozon/WB are parsed only from user-provided seed listing URLs.",
        "- No fallback search by brand/model is used.",
        "- Product pages are not opened in the main flow.",
        "- Official source is the model/spec/SEO reference.",
        "- Ozon/WB listing is the source for title/url/price/stock/ETA/bundle.",
        "- Same sellable variant from several listings is collapsed; lowest price wins.",
        "- Market ETA is copied to Kaspi without extra safety buffer.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    *,
    profiles: list[dict[str, Any]],
    seeds: list[dict[str, Any]],
    raw_cards: list[dict[str, Any]],
    listings: list[dict[str, Any]],
    scored_candidates: list[dict[str, Any]],
    best_result: dict[str, Any],
    source_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    out_dir = path_from_config("artifacts_market_discovery_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    built_at = now_iso()
    seed_errors = [r for r in source_reports if r.get("status") in {"failed", "empty"} or r.get("errors")]
    seed_warnings = [r for r in source_reports if r.get("warnings")]
    summary = {
        "profiles": len(profiles),
        "seed_urls": len(seeds),
        "raw_cards": len(raw_cards),
        "listing_cards": len(listings),
        **(best_result.get("summary", {}) or {}),
        "seed_errors": len(seed_errors),
        "seed_warnings": len(seed_warnings),
    }
    result = {
        "built_at": built_at,
        "mode": "seed_listing_only_no_fallback_search",
        "summary": summary,
        "records": best_result.get("records", []),
        "review_needed": best_result.get("review_needed", []),
        "rejected": best_result.get("rejected", []),
        "seed_reports": source_reports,
    }
    write_json(out_dir / "official_model_profiles.json", {"built_at": built_at, "profiles": profiles})
    write_json(out_dir / "market_seed_urls.json", {"built_at": built_at, "seeds": seeds})
    write_json(out_dir / "market_listing_raw_cards.json", {"built_at": built_at, "cards": raw_cards})
    write_json(out_dir / "market_listing_cards.json", {"built_at": built_at, "cards": listings})
    write_json(out_dir / "market_scored_candidates.json", {"built_at": built_at, "candidates": scored_candidates})
    write_json(out_dir / "market_best_offers.json", {"built_at": built_at, "records": best_result.get("records", [])})
    write_json(out_dir / "market_discovery_records.json", result)
    write_json(out_dir / "seed_url_report.json", {"built_at": built_at, "reports": source_reports})
    _write_seed_report(out_dir / "seed_url_report.txt", source_reports)
    _write_review_csv(out_dir / "market_review_needed.csv", best_result.get("review_needed", []))
    _write_report(out_dir / "market_discovery_report.txt", result)
    return result
