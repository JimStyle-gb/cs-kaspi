from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scripts.cs_kaspi.core.hash_utils import stable_hash
from scripts.cs_kaspi.core.paths import ROOT
from scripts.cs_kaspi.core.text_utils import normalize_spaces, slugify_ascii
from scripts.cs_kaspi.core.yaml_io import read_yaml

SUPPLIER_KEY = "demiand"
SUPPLIER_CONFIG_PATH = ROOT / "config" / "suppliers" / "demiand.yml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}

MAX_PRODUCT_KEY_LEN = 96

CATEGORY_SINGULAR = {
    "air_fryer_accessories": "air_fryer_accessory",
    "air_fryers": "air_fryer",
    "blenders": "blender",
    "coffee_makers": "coffee_maker",
    "ovens": "oven",
}

_SESSION: requests.Session | None = None


def get_config() -> dict[str, Any]:
    return read_yaml(SUPPLIER_CONFIG_PATH)


def _build_session() -> requests.Session:
    cfg = get_config().get("fetch_rules", {})
    retry = Retry(
        total=int(cfg.get("retry_count", 3)),
        connect=int(cfg.get("retry_count", 3)),
        read=int(cfg.get("retry_count", 3)),
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    session = requests.Session()
    session.headers.update(HEADERS)
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = _build_session()
    return _SESSION


def fetch_html(url: str, timeout: int | None = None) -> str:
    cfg_timeout = get_config().get("fetch_rules", {}).get("request_timeout_seconds", 45)
    timeout = int(timeout or cfg_timeout)
    response = get_session().get(url, timeout=(20, timeout))
    response.raise_for_status()
    response.encoding = response.encoding or response.apparent_encoding or "utf-8"
    return response.text


def make_soup(html_text: str) -> BeautifulSoup:
    return BeautifulSoup(html_text, "lxml")


def save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def input_dirs() -> dict[str, Path]:
    cfg = get_config()
    dirs = cfg.get("input_dirs", {})
    return {
        "catalog_pages": ROOT / dirs.get("catalog_pages_dir", "input/official/demiand/catalog_pages"),
        "product_pages": ROOT / dirs.get("product_pages_dir", "input/official/demiand/product_pages"),
        "manuals": ROOT / dirs.get("manuals_dir", "input/official/demiand/manuals"),
    }


def state_paths() -> dict[str, Path]:
    cfg = get_config()
    files = cfg.get("state_files", {})
    return {
        "product_index": ROOT / files.get("product_index_file", "artifacts/state/demiand_product_index.json"),
        "official_products": ROOT / files.get("official_products_file", "artifacts/state/demiand_official_products.json"),
    }


def category_key_from_name(name: str) -> str:
    mapping = get_config().get("category_mapping", {})
    return mapping.get(name, slugify_ascii(name))


def slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    return unquote(Path(path).name)


def parse_price_to_number(raw: str | None) -> int | None:
    if raw is None:
        return None
    digits = re.sub(r"[^0-9]", "", str(raw))
    return int(digits) if digits else None


def article_slug(article: str | None) -> str | None:
    slug = slugify_ascii((article or "").replace("/", " "))
    return slug or None


def compact_product_key(value: str, max_len: int = MAX_PRODUCT_KEY_LEN) -> str:
    value = re.sub(r"_+", "_", value).strip("_")
    if len(value) <= max_len:
        return value
    suffix = stable_hash(value)[:10]
    prefix = value[: max_len - len(suffix) - 1].rstrip("_")
    return f"{prefix}_{suffix}"


def build_product_key(category_key: str, slug_or_name: str | None, model_key: str | None = None, variant_key: str | None = None, article: str | None = None) -> str:
    category_part = CATEGORY_SINGULAR.get(category_key, slugify_ascii(category_key))
    base = slugify_ascii(model_key or slug_or_name or article or "product")
    article_part = article_slug(article)
    variant_part = slugify_ascii(variant_key) if variant_key else None

    pieces = [SUPPLIER_KEY, category_part]
    if category_key == "air_fryer_accessories":
        pieces.append(article_part or base)
    else:
        pieces.append(base or article_part or "product")
        if variant_part and variant_part not in pieces[-1]:
            pieces.append(variant_part)
        elif article_part and article_part not in pieces[-1]:
            article_extra = article_part
            if article_extra.startswith(f"{pieces[-1]}_"):
                article_extra = article_extra[len(pieces[-1]) + 1 :]
            if article_extra:
                pieces.append(article_extra)
    return compact_product_key("_".join(p for p in pieces if p))


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
        if isinstance(data, dict) and isinstance(data.get("@graph"), list):
            payloads.extend(item for item in data["@graph"] if isinstance(item, dict))
        elif isinstance(data, list):
            payloads.extend(item for item in data if isinstance(item, dict))
        elif isinstance(data, dict):
            payloads.append(data)
    return payloads


def clean_images(images: list[str]) -> list[str]:
    result: list[str] = []
    for img in images:
        value = normalize_spaces(str(img or ""))
        if not value or value == "#" or value.startswith("data:") or "lazy.svg" in value:
            continue
        if value not in result:
            result.append(value)
    return result


def product_hash(data: dict[str, Any]) -> str:
    return stable_hash(data)


def abs_url(base_url: str, href: str | None) -> str | None:
    if not href:
        return None
    return urljoin(base_url, href)
