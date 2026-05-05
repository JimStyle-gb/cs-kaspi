from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.json_io import read_json, write_json
from scripts.cs_kaspi.core.paths import path_from_config
from scripts.cs_kaspi.core.time_utils import now_iso

REVIEW_HEADERS = [
    "source", "seed_key", "market_title", "market_url", "market_price", "market_available",
    "market_stock", "eta_text", "lead_time_days", "brand", "model_key", "category_key",
    "base_product_key", "market_color", "market_bundle", "variant_signature", "match_confidence", "reason",
]

WB_MISSING_HEADERS = [
    "wb_id", "title", "url", "brand", "entity", "color", "last_price", "last_stock",
    "last_eta_text", "last_lead_time_days", "last_seen_at", "last_seed_keys", "manual_check_url", "status", "note",
]

WB_CURRENT_HEADERS = [
    "wb_id", "title", "url", "brand", "entity", "color", "price", "stock", "eta_text",
    "lead_time_days", "seed_keys", "first_seen_at", "last_seen_at",
]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple, set)):
        return " | ".join(_text(x) for x in value if _text(x))
    return str(value).strip()


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value)
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None


def _wb_id(card: dict[str, Any]) -> str:
    raw = card.get("market_id") or card.get("wb_id") or card.get("id")
    value = _as_int(raw)
    return str(value) if value else _text(raw)


def _wb_url(wb_id: str, fallback: Any = None) -> str:
    if wb_id:
        return f"https://www.wildberries.ru/catalog/{wb_id}/detail.aspx"
    return _text(fallback)


def _merge_seed_keys(existing: list[str], new_value: Any) -> list[str]:
    values = list(existing)
    if isinstance(new_value, list):
        candidates = new_value
    else:
        candidates = [_text(new_value)]
    for value in candidates:
        key = _text(value)
        if key and key not in values:
            values.append(key)
    return values


def _is_wb_sellable_card(card: dict[str, Any]) -> bool:
    if _text(card.get("source")).lower() != "wb":
        return False
    brand_id = _as_int(card.get("brand_id") or card.get("brandId"))
    brand_text = _text(card.get("brand") or card.get("supplier")).lower()
    if brand_id != 53038 and "demiand" not in brand_text:
        return False
    if not _wb_id(card):
        return False
    price = _as_int(card.get("price"))
    if not price or price <= 0:
        return False
    stock = _as_int(card.get("stock"))
    if stock is not None and stock <= 0:
        return False
    if card.get("available") is False:
        return False
    currency = _text(card.get("price_currency")).upper()
    if currency and currency != "KZT":
        return False
    return True


def _read_previous_wb_seen(path: Path) -> dict[str, dict[str, Any]]:
    data = read_json(path, default={})
    products = data.get("products", []) if isinstance(data, dict) else []
    result: dict[str, dict[str, Any]] = {}
    for row in products:
        if not isinstance(row, dict):
            continue
        wb_id = _text(row.get("wb_id"))
        if wb_id:
            result[wb_id] = row
    return result


def _build_current_wb_seen(
    raw_cards: list[dict[str, Any]],
    previous: dict[str, dict[str, Any]],
    built_at: str,
) -> dict[str, dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for card in raw_cards:
        if not isinstance(card, dict) or not _is_wb_sellable_card(card):
            continue
        wb_id = _wb_id(card)
        if not wb_id:
            continue
        price = _as_int(card.get("price"))
        stock = _as_int(card.get("stock"))
        previous_row = previous.get(wb_id, {})
        item = current.get(wb_id)
        if item is None:
            item = {
                "wb_id": wb_id,
                "title": _text(card.get("title") or card.get("market_title") or card.get("link_text")),
                "url": _wb_url(wb_id, card.get("url") or card.get("href")),
                "brand": _text(card.get("brand") or card.get("supplier") or "DEMIAND"),
                "brand_id": _as_int(card.get("brand_id") or card.get("brandId")),
                "entity": _text(card.get("wb_entity") or card.get("entity")),
                "color": _text(card.get("market_color_raw") or card.get("color_text") or card.get("market_color")),
                "price": price,
                "old_price": _as_int(card.get("old_price")),
                "stock": stock,
                "eta_text": _text(card.get("eta_text")),
                "lead_time_days": _as_int(card.get("lead_time_days")),
                "seed_keys": [],
                "first_seen_at": _text(previous_row.get("first_seen_at")) or built_at,
                "last_seen_at": built_at,
                "market_source": "wb_json_api",
                "manual_check_url": _wb_url(wb_id, card.get("url") or card.get("href")),
            }
            current[wb_id] = item
        # If the same WB ID appears through several seed/API sources, keep the lowest visible price.
        if price and (not item.get("price") or price < int(item.get("price") or 0)):
            item["price"] = price
            item["old_price"] = _as_int(card.get("old_price"))
            item["stock"] = stock
            item["eta_text"] = _text(card.get("eta_text"))
            item["lead_time_days"] = _as_int(card.get("lead_time_days"))
            item["url"] = _wb_url(wb_id, card.get("url") or card.get("href"))
            item["manual_check_url"] = item["url"]
        item["seed_keys"] = _merge_seed_keys(item.get("seed_keys") or [], card.get("seed_key"))
    return current


def _build_wb_missing_rows(previous: dict[str, dict[str, Any]], current: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current_ids = set(current)
    for wb_id, prev in sorted(previous.items(), key=lambda item: (_text(item[1].get("title")), item[0])):
        if wb_id in current_ids:
            continue
        rows.append({
            "wb_id": wb_id,
            "title": prev.get("title"),
            "url": _wb_url(wb_id, prev.get("url")),
            "brand": prev.get("brand"),
            "entity": prev.get("entity"),
            "color": prev.get("color"),
            "last_price": prev.get("price"),
            "last_stock": prev.get("stock"),
            "last_eta_text": prev.get("eta_text"),
            "last_lead_time_days": prev.get("lead_time_days"),
            "last_seen_at": prev.get("last_seen_at"),
            "last_seed_keys": prev.get("seed_keys") or [],
            "manual_check_url": _wb_url(wb_id, prev.get("manual_check_url") or prev.get("url")),
            "status": "missing_from_current_wb_api",
            "note": "Не возвращать автоматически в ready. Проверить ссылку вручную; если товара нет в наличии на WB, это нормальное поведение.",
        })
    return rows


def _write_dict_rows_csv(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _text(row.get(key)) for key in headers})


def _write_wb_current_csv(path: Path, products: dict[str, dict[str, Any]]) -> None:
    rows = [products[key] for key in sorted(products, key=lambda x: int(x) if x.isdigit() else x)]
    _write_dict_rows_csv(path, rows, WB_CURRENT_HEADERS)


def _write_wb_missing_txt(path: Path, *, previous_count: int, current_count: int, missing_rows: list[dict[str, Any]]) -> None:
    lines = [
        "CS-Kaspi WB missing products audit",
        "Правило: если WB-товар пропал из текущей выдачи, он НЕ возвращается в ready/create автоматически.",
        "Нужно проверить ссылку вручную; если товара нет в наличии на WB, это нормальное поведение.",
        "",
        f"previous_seen_products: {previous_count}",
        f"current_seen_products: {current_count}",
        f"missing_products: {len(missing_rows)}",
        "",
    ]
    if not missing_rows:
        lines.append("missing: none")
    for idx, row in enumerate(missing_rows, 1):
        lines.append(f"{idx}. {row.get('title') or '-'}")
        lines.append(f"   wb_id: {row.get('wb_id')}")
        lines.append(f"   link: {row.get('manual_check_url')}")
        lines.append(f"   last_price: {row.get('last_price')} KZT")
        lines.append(f"   last_stock: {row.get('last_stock')}")
        lines.append(f"   last_eta: {row.get('last_eta_text') or row.get('last_lead_time_days') or '-'}")
        lines.append(f"   last_seen_at: {row.get('last_seen_at') or '-'}")
        lines.append(f"   last_seed_keys: {_text(row.get('last_seed_keys')) or '-'}")
        lines.append("   action: вручную открыть ссылку; если нет наличия — товар правильно не попал в кандидаты.")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _build_wb_seen_audit(raw_cards: list[dict[str, Any]], built_at: str) -> dict[str, Any]:
    state_dir = path_from_config("artifacts_state_dir")
    state_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = state_dir / "wb_seen_products_baseline.json"
    previous = _read_previous_wb_seen(baseline_path)
    current = _build_current_wb_seen(raw_cards, previous, built_at)
    missing_rows = _build_wb_missing_rows(previous, current)
    current_rows = [current[key] for key in sorted(current, key=lambda x: int(x) if x.isdigit() else x)]

    baseline = {
        "built_at": built_at,
        "note": "Autogenerated current WB sellable DEMIAND baseline. Restored between GitHub runs through actions/cache when workflow cache is enabled.",
        "products_count": len(current_rows),
        "products": current_rows,
    }
    write_json(baseline_path, baseline)
    return {
        "previous_count": len(previous),
        "current_count": len(current),
        "missing_count": len(missing_rows),
        "current_rows": current_rows,
        "missing_rows": missing_rows,
        "baseline_path": baseline_path.as_posix(),
    }


def _write_variant_collapse_audit_txt(path: Path, groups: list[dict[str, Any]]) -> None:
    lines = [
        "CS-Kaspi WB variant collapse audit",
        "Правило: схлопываются только точные дубли одного sellable-варианта; отличия по цвету/комплекту/типу/аксессуару остаются отдельными Kaspi-кандидатами.",
        "",
    ]
    if not groups:
        lines.append("duplicate_groups: 0")
    for idx, group in enumerate(groups, 1):
        lines.append(f"#{idx} {group.get('chosen_title')}")
        lines.append(f"  variant_key: {group.get('variant_key')}")
        lines.append(f"  color: {group.get('market_color') or '-'}")
        lines.append(f"  bundle: {group.get('market_bundle') or '-'}")
        lines.append(f"  wb_entity: {group.get('wb_entity') or '-'}")
        lines.append(f"  collapsed_count: {group.get('collapsed_count')}")
        lines.append(f"  chosen_market_id: {group.get('chosen_market_id')}")
        lines.append(f"  chosen_price: {group.get('chosen_price')}")
        lines.append("  offers:")
        for offer in group.get('offers') or []:
            lines.append(
                "    - "
                f"id={offer.get('market_id')} "
                f"root={offer.get('wb_root') or '-'} "
                f"supplier={offer.get('wb_supplier_id') or '-'} "
                f"price={offer.get('price')} "
                f"stock={offer.get('stock')} "
                f"eta={offer.get('lead_time_days')} "
                f"seed={offer.get('seed_key')} "
                f"url={offer.get('url')}"
            )
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_variant_collapse_audit_csv(path: Path, groups: list[dict[str, Any]]) -> None:
    headers = [
        "group_no", "market_product_key", "variant_key", "chosen_market_id", "chosen_price",
        "chosen_title", "market_color", "market_bundle", "wb_entity", "collapsed_count",
        "offer_market_id", "offer_wb_root", "offer_wb_supplier_id", "offer_price",
        "offer_stock", "offer_eta_days", "offer_seed_key", "offer_url",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for idx, group in enumerate(groups, 1):
            for offer in group.get('offers') or []:
                writer.writerow({
                    "group_no": idx,
                    "market_product_key": group.get("market_product_key"),
                    "variant_key": group.get("variant_key"),
                    "chosen_market_id": group.get("chosen_market_id"),
                    "chosen_price": group.get("chosen_price"),
                    "chosen_title": group.get("chosen_title"),
                    "market_color": group.get("market_color"),
                    "market_bundle": group.get("market_bundle"),
                    "wb_entity": group.get("wb_entity"),
                    "collapsed_count": group.get("collapsed_count"),
                    "offer_market_id": offer.get("market_id"),
                    "offer_wb_root": offer.get("wb_root"),
                    "offer_wb_supplier_id": offer.get("wb_supplier_id"),
                    "offer_price": offer.get("price"),
                    "offer_stock": offer.get("stock"),
                    "offer_eta_days": offer.get("lead_time_days"),
                    "offer_seed_key": offer.get("seed_key"),
                    "offer_url": offer.get("url"),
                })


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
    lines = ["CS-Kaspi v7 WB-only seed listing report", ""]
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
        "CS-Kaspi v7 WB-only market discovery report",
        f"built_at: {result.get('built_at')}",
        f"mode: {result.get('mode')}",
        f"official_profiles: {summary.get('profiles', 0)}",
        f"seed_urls: {summary.get('seed_urls', 0)}",
        f"raw_cards: {summary.get('raw_cards', 0)}",
        f"listing_cards: {summary.get('listing_cards', 0)}",
        f"scored_candidates: {summary.get('scored_candidates', 0)}",
        f"auto_best_offer_records: {summary.get('auto_best_offer_records', 0)}",
        f"duplicates_collapsed: {summary.get('duplicates_collapsed', 0)}",
        f"duplicate_groups: {summary.get('duplicate_groups', 0)}",
        f"review_needed: {summary.get('review_needed', 0)}",
        f"rejected: {summary.get('rejected', 0)}",
        f"seed_errors: {summary.get('seed_errors', 0)}",
        f"seed_warnings: {summary.get('seed_warnings', 0)}",
        f"wb_seen_products_previous: {summary.get('wb_seen_products_previous', 0)}",
        f"wb_seen_products_current: {summary.get('wb_seen_products_current', 0)}",
        f"wb_missing_products: {summary.get('wb_missing_products', 0)}",
        "",
        "Rules:",
        "- WB are parsed only from user-provided seed listing URLs.",
        "- No fallback search by brand/model is used.",
        "- Product pages are not opened in the main flow.",
        "- Official source is the model/spec/SEO reference.",
        "- WB listing is the source for title/url/price/stock/ETA/bundle.",
        "- Same exact sellable variant from several listings is collapsed; lowest price wins.",
        "- Missing previous WB products are only reported for manual check; they are not forced back into ready.",
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
    wb_seen_audit = _build_wb_seen_audit(raw_cards, built_at)
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
        "wb_seen_products_previous": wb_seen_audit.get("previous_count", 0),
        "wb_seen_products_current": wb_seen_audit.get("current_count", 0),
        "wb_missing_products": wb_seen_audit.get("missing_count", 0),
    }
    result = {
        "built_at": built_at,
        "mode": "wb_seed_listing_only_no_fallback_search",
        "summary": summary,
        "records": best_result.get("records", []),
        "review_needed": best_result.get("review_needed", []),
        "rejected": best_result.get("rejected", []),
        "seed_reports": source_reports,
        "wb_missing_products": wb_seen_audit.get("missing_rows", []),
    }
    write_json(out_dir / "official_model_profiles.json", {"built_at": built_at, "profiles": profiles})
    write_json(out_dir / "market_seed_urls.json", {"built_at": built_at, "seeds": seeds})
    write_json(out_dir / "market_listing_raw_cards.json", {"built_at": built_at, "cards": raw_cards})
    write_json(out_dir / "market_listing_cards.json", {"built_at": built_at, "cards": listings})
    write_json(out_dir / "market_scored_candidates.json", {"built_at": built_at, "candidates": scored_candidates})
    write_json(out_dir / "market_best_offers.json", {"built_at": built_at, "records": best_result.get("records", [])})
    write_json(out_dir / "market_variant_collapse_audit.json", {"built_at": built_at, "groups": best_result.get("duplicate_groups", [])})
    _write_variant_collapse_audit_txt(out_dir / "market_variant_collapse_audit.txt", best_result.get("duplicate_groups", []))
    _write_variant_collapse_audit_csv(out_dir / "market_variant_collapse_audit.csv", best_result.get("duplicate_groups", []))
    write_json(out_dir / "wb_seen_products_current.json", {
        "built_at": built_at,
        "products_count": wb_seen_audit.get("current_count", 0),
        "products": wb_seen_audit.get("current_rows", []),
    })
    _write_wb_current_csv(out_dir / "wb_seen_products_current.csv", {
        row.get("wb_id"): row for row in wb_seen_audit.get("current_rows", []) if row.get("wb_id")
    })
    write_json(out_dir / "wb_missing_products_audit.json", {
        "built_at": built_at,
        "previous_seen_products": wb_seen_audit.get("previous_count", 0),
        "current_seen_products": wb_seen_audit.get("current_count", 0),
        "missing_products_count": wb_seen_audit.get("missing_count", 0),
        "missing_products": wb_seen_audit.get("missing_rows", []),
    })
    _write_wb_missing_txt(
        out_dir / "wb_missing_products_audit.txt",
        previous_count=int(wb_seen_audit.get("previous_count") or 0),
        current_count=int(wb_seen_audit.get("current_count") or 0),
        missing_rows=wb_seen_audit.get("missing_rows", []),
    )
    _write_dict_rows_csv(out_dir / "wb_missing_products_audit.csv", wb_seen_audit.get("missing_rows", []), WB_MISSING_HEADERS)
    write_json(out_dir / "market_discovery_records.json", result)
    write_json(out_dir / "seed_url_report.json", {"built_at": built_at, "reports": source_reports})
    _write_seed_report(out_dir / "seed_url_report.txt", source_reports)
    _write_review_csv(out_dir / "market_review_needed.csv", best_result.get("review_needed", []))
    _write_report(out_dir / "market_discovery_report.txt", result)
    return result
