from __future__ import annotations

from scripts.cs_kaspi.core.paths import project_config
from scripts.cs_kaspi.core.text_utils import normalize_spaces


def _clean_image(value: str | None) -> str:
    img = normalize_spaces(str(value or ""))
    if not img or img == "#" or img.startswith("data:") or "lazy.svg" in img:
        return ""
    if not img.startswith(("http://", "https://")):
        return ""
    return img


def _append_unique(images: list[str], value: str | None, max_images: int) -> None:
    img = _clean_image(value)
    if img and img not in images and len(images) < max_images:
        images.append(img)


def _market_images(product: dict, max_images: int) -> list[str]:
    market = product.get("market", {}) or {}
    images: list[str] = []
    _append_unique(images, market.get("market_image"), max_images)
    for source in (market.get("sources") or {}).values():
        if isinstance(source, dict):
            _append_unique(images, source.get("image"), max_images)
    return images


def _official_images(product: dict, max_images: int) -> list[str]:
    images: list[str] = []
    for img in product.get("official", {}).get("images", []) or []:
        _append_unique(images, img, max_images)
    return images


def run(product: dict) -> list[str]:
    """Собирает фото для Kaspi с защитой от таймаутов official-сайта.

    Правило проекта: official-фото остаются приоритетом для качества, но у каждого WB-ready
    товара должен быть хотя бы один WB-image fallback. Если demiand.ru временно не отдаёт фото,
    image package всё равно сможет собрать изображение по WB-карточке.
    """
    max_images = int(project_config().get("runtime", {}).get("max_kaspi_images", 10))
    max_images = max(1, min(10, max_images))

    official = _official_images(product, max_images)
    market = _market_images(product, max_images)
    images: list[str] = []

    # Если есть WB-фото, оставляем под него минимум один слот.
    official_limit = max_images - 1 if market else max_images
    for img in official[:official_limit]:
        _append_unique(images, img, max_images)

    for img in market:
        _append_unique(images, img, max_images)

    # Если official-фото было меньше лимита или WB-фото уже дублировалось, дозаполняем остаток.
    for img in official[official_limit:]:
        _append_unique(images, img, max_images)

    return images
