from __future__ import annotations

from scripts.cs_kaspi.core.paths import project_config
from scripts.cs_kaspi.core.text_utils import normalize_spaces


def run(product: dict) -> list[str]:
    max_images = int(project_config().get("runtime", {}).get("max_kaspi_images", 10))
    images: list[str] = []
    for img in product.get("official", {}).get("images", []) or []:
        value = normalize_spaces(str(img or ""))
        if not value or value == "#" or value.startswith("data:") or "lazy.svg" in value:
            continue
        if value not in images:
            images.append(value)
        if len(images) >= max_images:
            break
    return images
