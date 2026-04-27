from __future__ import annotations


def run(product: dict) -> str:
    official = product.get("official", {})
    return (
        official.get("description_official")
        or official.get("description")
        or official.get("short_description")
        or ""
    )
