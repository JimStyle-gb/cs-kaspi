from __future__ import annotations

import csv
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from scripts.cs_kaspi.core.paths import path_from_config


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _split_urls(value: Any) -> list[str]:
    raw = _text(value)
    if not raw:
        return []
    urls = [x.strip() for x in re.split(r"[,;\n]+", raw) if x.strip().startswith(("http://", "https://"))]
    return list(dict.fromkeys(urls))[:10]


def _safe_ext(url: str) -> str:
    path = urlparse(url).path.lower()
    suffix = Path(path).suffix
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return suffix
    return ".jpg"


def _download(url: str, path: Path, timeout: int) -> str:
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "CS-Kaspi/1.0"})
        response.raise_for_status()
        if not response.content:
            return "empty_response"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
        return "downloaded"
    except Exception as exc:
        return f"failed:{exc}"


def write_image_manifest(data: dict[str, Any]) -> dict[str, Path]:
    """
    Готовит manifest/queue для Kaspi images/<merchant_sku>/.

    По умолчанию реальные фото не скачиваются, чтобы обычный build_all не раздувал artifacts.
    Для полной image-package сборки включить переменную окружения:
    CS_KASPI_DOWNLOAD_IMAGES=1
    """
    out_dir = path_from_config("artifacts_exports_dir")
    images_dir = out_dir / "kaspi_images" / "images"
    manifest_path = out_dir / "kaspi_images_manifest.csv"
    queue_path = out_dir / "kaspi_images_download_queue.txt"
    download_enabled = os.environ.get("CS_KASPI_DOWNLOAD_IMAGES", "").strip().lower() in {"1", "true", "yes", "on"}
    timeout = int(os.environ.get("CS_KASPI_IMAGE_TIMEOUT_SEC", "30") or "30")

    rows: list[dict[str, Any]] = []
    queue_lines: list[str] = []
    ready_by_template = data.get("ready_by_template") or {}
    for template_key, payloads in sorted(ready_by_template.items()):
        for payload in payloads:
            row = payload.get("row") or {}
            sku = _text(row.get("merchant_sku") or row.get("image_code") or payload.get("product_key")).strip()
            if not sku:
                continue
            urls = _split_urls(row.get("image_urls"))
            for idx, url in enumerate(urls, 1):
                filename = f"{idx:02d}{_safe_ext(url)}"
                rel_path = f"images/{sku}/{filename}"
                status = "queued"
                if download_enabled:
                    status = _download(url, images_dir / sku / filename, timeout)
                rows.append({
                    "template_key": template_key,
                    "product_key": payload.get("product_key"),
                    "merchant_sku": sku,
                    "image_index": idx,
                    "source_url": url,
                    "kaspi_image_path": rel_path,
                    "status": status,
                })
                queue_lines.append(f"{rel_path}\t{url}")

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["template_key", "product_key", "merchant_sku", "image_index", "source_url", "kaspi_image_path", "status"],
        )
        writer.writeheader()
        writer.writerows(rows)
    queue_path.write_text("\n".join(queue_lines).rstrip() + ("\n" if queue_lines else ""), encoding="utf-8")
    return {
        "images_manifest_csv": manifest_path,
        "images_download_queue_txt": queue_path,
    }
