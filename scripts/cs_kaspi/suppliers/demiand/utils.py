from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scripts.cs_kaspi.core.read_yaml import read_yaml
from scripts.cs_kaspi.core.file_paths import ROOT

SUPPLIER_CONFIG_PATH = ROOT / "config" / "suppliers" / "demiand.yml"
MODEL_SPECS_PATH = ROOT / "config" / "model_specs" / "demiand_air_fryers.yml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}

_SESSION: requests.Session | None = None


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session


def get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = _build_session()
    return _SESSION


def get_supplier_config() -> dict[str, Any]:
    return read_yaml(SUPPLIER_CONFIG_PATH)


def get_model_specs() -> dict[str, Any]:
    return read_yaml(MODEL_SPECS_PATH)


def fetch_html(url: str, timeout: int = 60) -> str:
    response = get_session().get(url, timeout=(20, timeout))
    response.raise_for_status()
    response.encoding = response.encoding or response.apparent_encoding or "utf-8"
    return response.text


def save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def slug_from_url(url: str) -> str:
    return Path(urlparse(url).path.strip("/")).name


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def parse_price_to_number(raw: str | None) -> int | None:
    if not raw:
        return None
    digits = re.sub(r"[^0-9]", "", raw)
    return int(digits) if digits else None


def build_product_key(category_key: str, slug: str) -> str:
    return f"demiand_{category_key.rstrip('s')}_{slug.replace('-', '_')}"


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
