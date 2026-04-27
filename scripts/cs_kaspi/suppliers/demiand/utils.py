from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, unquote

import requests
from bs4 import BeautifulSoup

from scripts.cs_kaspi.core.read_yaml import read_yaml
from scripts.cs_kaspi.core.file_paths import ROOT

SUPPLIER_CONFIG_PATH = ROOT / "config" / "suppliers" / "demiand.yml"
MODEL_SPECS_PATH = ROOT / "config" / "model_specs" / "demiand_air_fryers.yml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}

CATEGORY_SINGULAR = {
    "air_fryers": "air_fryer",
    "air_fryer_accessories": "air_fryer_accessory",
    "blenders": "blender",
    "coffee_makers": "coffee_maker",
    "ovens": "oven",
}


def get_supplier_config() -> dict[str, Any]:
    return read_yaml(SUPPLIER_CONFIG_PATH)


def get_model_specs() -> dict[str, Any]:
    return read_yaml(MODEL_SPECS_PATH)


def fetch_html(url: str, timeout: int = 30) -> str:
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    return response.text


def save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def slug_from_url(url: str) -> str:
    raw = Path(urlparse(url).path.strip("/")).name
    return unquote(raw)


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def parse_price_to_number(raw: str | None) -> int | None:
    if not raw:
        return None
    digits = re.sub(r"[^0-9]", "", raw)
    return int(digits) if digits else None


def slugify_key(text: str | None) -> str:
    text = unquote(text or "").lower().replace("ё", "е")
    text = text.replace("wifi", " wifi ")
    text = re.sub(r"[^a-zа-я0-9]+", "_", text, flags=re.IGNORECASE)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def article_slug(article: str | None) -> str | None:
    if not article:
        return None
    return slugify_key(article.replace("/", " ")) or None


def build_product_key(
    category_key: str,
    slug_or_name: str,
    model_key: str | None = None,
    variant_key: str | None = None,
    article: str | None = None,
) -> str:
    category_part = CATEGORY_SINGULAR.get(category_key, category_key.rstrip("s"))
    article_part = article_slug(article)
    base_slug = slugify_key(model_key or slug_or_name)
    variant_slug = slugify_key(variant_key) if variant_key else None

    pieces = ["demiand", category_part]

    if category_key == "air_fryer_accessories":
        # Для аксессуаров ключ должен строиться от самого товара/артикула,
        # а не от совместимой модели (Tison/Waison), иначе разные аксессуары сливаются.
        if article_part:
            pieces.append(article_part)
        else:
            pieces.append(base_slug)
        return "_".join([p for p in pieces if p])

    pieces.append(base_slug or article_part or slugify_key(slug_or_name))
    if variant_slug and variant_slug not in pieces[-1]:
        pieces.append(variant_slug)
    elif article_part and article_part not in pieces[-1]:
        pieces.append(article_part)
    return "_".join([p for p in pieces if p])


def make_soup(html_text: str) -> BeautifulSoup:
    return BeautifulSoup(html_text, "lxml")


def extract_json_ld(soup: BeautifulSoup) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.get_text(strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if isinstance(data, dict) and "@graph" in data and isinstance(data["@graph"], list):
            payloads.extend([item for item in data["@graph"] if isinstance(item, dict)])
        elif isinstance(data, list):
            payloads.extend([item for item in data if isinstance(item, dict)])
        elif isinstance(data, dict):
            payloads.append(data)
    return payloads


def category_key_from_supplier_name(name: str, mapping: dict[str, str]) -> str:
    return mapping.get(name, re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_"))


def category_dirs() -> dict[str, Path]:
    cfg = get_supplier_config()
    paths = cfg.get("input_dirs", {})
    return {
        "catalog_pages": ROOT / paths.get("catalog_pages_dir", "input/official/demiand/catalog_pages"),
        "product_pages": ROOT / paths.get("product_pages_dir", "input/official/demiand/product_pages"),
        "manuals": ROOT / paths.get("manuals_dir", "input/official/demiand/manuals"),
    }


def supplier_state_paths() -> dict[str, Path]:
    cfg = get_supplier_config()
    files = cfg.get("state_files", {})
    return {
        "product_index": ROOT / files.get("product_index_file", "artifacts/state/demiand_product_index.json"),
        "official_products": ROOT / files.get("official_products_file", "artifacts/state/demiand_official_products.json"),
        "supplier_state": ROOT / files.get("supplier_state_file", "artifacts/state/official_state.json"),
    }
