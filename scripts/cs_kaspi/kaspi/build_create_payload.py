from __future__ import annotations
def run(plan: dict) -> dict:
    return {"items": plan.get("products",[])}
