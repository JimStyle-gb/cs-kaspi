from __future__ import annotations


def run(product: dict, price: int | None, stock: int) -> dict:
    official = product.get("official", {}) or {}
    market = product.get("market", {}) or {}
    problems: list[str] = []

    if not official.get("exists"):
        problems.append("no_official_product")
    if not official.get("title_official"):
        problems.append("missing_official_title")
    if not product.get("category_key"):
        problems.append("missing_category_key")
    if not product.get("official", {}).get("images"):
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
    }
