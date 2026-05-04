from __future__ import annotations

from scripts.cs_kaspi.core.paths import project_config
from scripts.cs_kaspi.core.text_utils import normalize_spaces


def _add(images: list[str], value: str | None, max_images: int) -> None:
    img = normalize_spaces(str(value or ""))
    if not img or img == "#" or img.startswith("data:") or "lazy.svg" in img:
        return
    if img not in images and len(images) < max_images:
        images.append(img)


def run(product: dict) -> list[str]:
    max_images = int(project_config().get("runtime", {}).get("max_kaspi_images", 10))
    images: list[str] = []
    for img in product.get("official", {}).get("images", []) or []:
        _add(images, img, max_images)
    market = product.get("market", {}) or {}
    _add(images, market.get("market_image"), max_images)
    for source in (market.get("sources") or {}).values():
        if isinstance(source, dict):
            _add(images, source.get("image"), max_images)
    return images
