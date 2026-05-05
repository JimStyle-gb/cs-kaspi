from __future__ import annotations


def run(product: dict, price: int | None, stock: int) -> dict:
    official = product.get("official", {}) or {}
    market = product.get("market", {}) or {}
    kaspi_images = product.get("kaspi_policy", {}).get("kaspi_images") if isinstance(product.get("kaspi_policy"), dict) else None
    problems: list[str] = []
    is_market_only = product.get("is_market_only") is True or official.get("status") == "market_only_wb"

    if not official.get("exists") and not is_market_only:
        problems.append("no_official_product")
    if not official.get("title_official"):
        problems.append("missing_title")
    if not product.get("category_key"):
        problems.append("missing_category_key")
    images = official.get("images") or []
    market_image = market.get("market_image")
    if not images and not market_image and not kaspi_images:
        problems.append("missing_images")

    if market.get("sellable") is True and price and stock > 0 and not problems:
        lifecycle_status = "kaspi_ready"
        action_status = "ready_for_create_or_update"
    elif problems:
        lifecycle_status = "needs_review"
        action_status = "manual_review"
    else:
        lifecycle_status = "catalog_only"
        action_status = "wait_market_data"

    return {
        "lifecycle_status": lifecycle_status,
        "action_status": action_status,
        "needs_review": bool(problems),
        "review_reasons": problems,
        "market_sellable": bool(market.get("sellable")),
        "official_enrichment": "missing_market_only" if is_market_only else "official_enriched",
        "eta_status": market.get("eta_status"),
    }
