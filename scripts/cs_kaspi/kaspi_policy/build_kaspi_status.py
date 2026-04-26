from __future__ import annotations
def run(product: dict) -> dict:
    official_exists=product.get("official",{}).get("exists",False)
    market_sellable=product.get("market",{}).get("sellable",False)
    if not official_exists:
        lifecycle, market_status, kaspi_status, action_status = "blocked","not_found","blocked","skip"
    elif market_sellable:
        lifecycle, market_status, kaspi_status, action_status = "kaspi_ready","found","ready","create"
    else:
        lifecycle, market_status, kaspi_status, action_status = "catalog_only","not_found","paused","pause"
    return {"lifecycle_status":lifecycle,"official_status":"active" if official_exists else "missing","market_status":market_status,"kaspi_status":kaspi_status,"action_status":action_status,"needs_review":False,"manual_blocked":False,"review_reason":None}
