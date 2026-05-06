from __future__ import annotations

import csv
import os
import re
import shutil
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageOps, UnidentifiedImageError

from scripts.cs_kaspi.core.json_io import write_json
from scripts.cs_kaspi.core.paths import ROOT, path_from_config
from scripts.cs_kaspi.core.yaml_io import read_yaml


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "да"}


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _settings() -> dict[str, Any]:
    cfg = read_yaml(ROOT / "config" / "kaspi.yml")
    image_cfg = (cfg.get("image_package") or {}) if isinstance(cfg, dict) else {}
    max_side_px = _int(image_cfg.get("max_side_px"), 0)
    if max_side_px < 0:
        max_side_px = 0
    return {
        "enabled": _bool(image_cfg.get("enabled"), True),
        "download_images": _bool(image_cfg.get("download_images"), True),
        "create_zip": _bool(image_cfg.get("create_zip"), True),
        "keep_unzipped_images": _bool(image_cfg.get("keep_unzipped_images"), False),
        "output_format": "jpg",
        # 0 = не уменьшать фото. Для проекта важнее качество карточки, чем минимальный вес artifact.
        "max_side_px": max_side_px,
        # JPG/JPEG из источника сохраняются как есть, без пережатия. Quality применяется только к PNG/WebP/другим форматам.
        "jpeg_quality": max(85, min(100, _int(image_cfg.get("jpeg_quality"), 95))),
        "max_images_per_product": max(1, min(10, _int(image_cfg.get("max_images_per_product"), 10))),
        "min_images_per_product": max(1, min(10, _int(image_cfg.get("min_images_per_product"), 1))),
        "timeout_sec": max(3, _int(image_cfg.get("timeout_sec"), 12)),
        "retries": max(0, min(3, _int(image_cfg.get("retries"), 1))),
        "min_bytes": max(0, _int(image_cfg.get("min_bytes"), 512)),
        "user_agent": _text(image_cfg.get("user_agent") or "CS-Kaspi/1.0"),
    }


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on", "да"}


def _split_urls(value: Any, limit: int) -> list[str]:
    raw = _text(value)
    if not raw:
        return []
    urls = [x.strip() for x in re.split(r"[,;\n]+", raw) if x.strip().startswith(("http://", "https://"))]
    return list(dict.fromkeys(urls))[:limit]


def _safe_sku(value: str) -> str:
    sku = re.sub(r"[^0-9A-Za-zА-Яа-я._-]+", "_", value.strip())
    return sku.strip("._-") or "missing_sku"


def _is_jpeg_bytes(content: bytes) -> bool:
    return len(content) >= 3 and content[:3] == b"\xff\xd8\xff"


def _to_jpeg_bytes(content: bytes, *, quality: int, max_side_px: int) -> tuple[bytes, str]:
    """Готовит фото для Kaspi без лишней потери качества.

    Важное правило проекта:
    - если источник уже JPG/JPEG, сохраняем байты как есть, без re-encode и без resize;
    - если источник WebP/PNG/другой формат, конвертируем в JPG с высоким качеством;
    - max_side_px=0 означает не уменьшать размер изображения.
    """
    if _is_jpeg_bytes(content):
        return content, "source_jpeg_copied_without_reencode"

    with Image.open(BytesIO(content)) as image:
        image = ImageOps.exif_transpose(image)
        source_format = (image.format or "image").lower()
        if max_side_px and max_side_px > 0 and max(image.size) > max_side_px:
            image.thumbnail((max_side_px, max_side_px), Image.Resampling.LANCZOS)
            resize_detail = f"resized_max_side_{max_side_px}"
        else:
            resize_detail = "original_dimensions_kept"
        if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
            rgba = image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            image = Image.alpha_composite(background, rgba).convert("RGB")
        else:
            image = image.convert("RGB")
        out = BytesIO()
        image.save(out, format="JPEG", quality=quality, optimize=False, subsampling=0)
        return out.getvalue(), f"converted_from_{source_format}_quality_{quality}_{resize_detail}"


def _download(
    session: requests.Session,
    url: str,
    target_base: Path,
    timeout: int,
    retries: int,
    min_bytes: int,
    jpeg_quality: int,
    max_side_px: int,
) -> tuple[str, Path | None, int, str]:
    """Скачивает фото, конвертирует в .jpg и не роняет весь build_all при одной битой ссылке."""
    path = target_base.with_suffix(".jpg")
    if path.exists() and path.stat().st_size >= max(min_bytes, 1):
        return "cached", path, path.stat().st_size, "existing_jpg"

    last_detail = ""
    for attempt in range(retries + 1):
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            content = response.content or b""
            if min_bytes and len(content) < min_bytes:
                return "failed_small_file", None, len(content), f"source_bytes={len(content)}"
            try:
                jpg, detail = _to_jpeg_bytes(content, quality=jpeg_quality, max_side_px=max_side_px)
            except UnidentifiedImageError as exc:
                return "failed_bad_image", None, len(content), str(exc)
            if min_bytes and len(jpg) < min_bytes:
                return "failed_small_jpg", None, len(jpg), f"jpg_bytes={len(jpg)}"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(jpg)
            return "downloaded", path, len(jpg), detail
        except Exception as exc:
            last_detail = str(exc)
            if attempt >= retries:
                break
    return "failed", None, 0, last_detail


def _is_optional_unavailable_image(status: str, detail: str, product_has_image: bool) -> bool:
    """Определяет битую необязательную ссылку на фото.

    WB иногда оставляет в списке 10-е/резервное фото, которое уже отдаёт 404.
    Если у товара уже есть хотя бы одно нормальное фото, такая ссылка не должна портить
    общий статус image package как failed. Мы не добавляем её в manifest/queue и считаем
    отдельно как skipped_optional_unavailable.
    """
    if not product_has_image:
        return False
    if status not in {"failed", "failed_small_file", "failed_small_jpg", "failed_bad_image"}:
        return False
    text = f"{status} {detail}".lower()
    return "404" in text or "410" in text or "not found" in text


def _write_zip(zip_path: Path, package_dir: Path, downloaded_paths: list[Path]) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if not downloaded_paths:
            zf.writestr("README.txt", "No images were downloaded. Check kaspi_images_manifest.csv.\n")
            return
        for path in sorted(dict.fromkeys(downloaded_paths)):
            if path.exists() and path.is_file():
                zf.write(path, path.relative_to(package_dir).as_posix())


def _cleanup_unzipped_images(package_dir: Path, keep_unzipped_images: bool, zip_created: bool) -> bool:
    if keep_unzipped_images or not zip_created or not package_dir.exists():
        return package_dir.exists()
    shutil.rmtree(package_dir, ignore_errors=True)
    return False


def write_image_manifest(data: dict[str, Any]) -> dict[str, Path]:
    """
    Собирает Kaspi image package:
    - artifacts/exports/kaspi_images.zip с путями images/<merchant_sku>/01.jpg
    - manifest/queue/summary для аудита.

    Правило проекта по фото:
    - цель не скачать все 10 фото любой ценой;
    - товар считается image-ok, если скачалось минимум min_images_per_product фото;
    - дополнительные битые/timeout/404 ссылки после достижения минимума считаются optional skipped,
      не портят общий статус и не попадают в manifest/queue;
    - если скачалось меньше минимума, товар получает image warning через summary/manifest.

    Качество не режем: JPG/JPEG источника копируется как есть, WebP/PNG конвертируются
    в JPG с высоким качеством без уменьшения размера, если max_side_px=0.

    По умолчанию распакованная папка artifacts/exports/kaspi_images удаляется после создания ZIP,
    чтобы GitHub artifact не хранил одни и те же фото два раза.

    Быстрые override-переменные:
    - CS_KASPI_DOWNLOAD_IMAGES=0 — только manifest/queue без скачивания.
    - CS_KASPI_DOWNLOAD_IMAGES=1 — принудительно скачать фото.
    - CS_KASPI_KEEP_UNZIPPED_IMAGES=1 — оставить папку kaspi_images для ручной проверки.
    """
    out_dir = path_from_config("artifacts_exports_dir")
    settings = _settings()
    enabled = _env_bool("CS_KASPI_IMAGE_PACKAGE", bool(settings["enabled"]))
    download_enabled = _env_bool("CS_KASPI_DOWNLOAD_IMAGES", bool(settings["download_images"]))
    create_zip = _env_bool("CS_KASPI_CREATE_IMAGES_ZIP", bool(settings["create_zip"]))
    keep_unzipped_images = _env_bool("CS_KASPI_KEEP_UNZIPPED_IMAGES", bool(settings["keep_unzipped_images"]))
    min_images_per_product = int(settings.get("min_images_per_product") or 1)

    package_dir = out_dir / "kaspi_images"
    images_dir = package_dir / "images"
    manifest_path = out_dir / "kaspi_images_manifest.csv"
    queue_path = out_dir / "kaspi_images_download_queue.txt"
    summary_path = out_dir / "kaspi_images_summary.json"
    zip_path = out_dir / "kaspi_images.zip"

    rows: list[dict[str, Any]] = []
    queue_lines: list[str] = []
    downloaded_paths: list[Path] = []
    product_summaries: list[dict[str, Any]] = []
    stats = {
        "products": 0,
        "products_image_ok": 0,
        "products_below_min_images": 0,
        "products_without_urls": 0,
        "urls_total": 0,
        "source_urls_seen": 0,
        "downloaded": 0,
        "cached": 0,
        "queued_only": 0,
        # failed = только реальные проблемы, когда у товара меньше минимального числа рабочих фото.
        "failed": 0,
        # skipped_optional_unavailable = дополнительные ссылки не скачались, но минимум фото у товара уже есть.
        "skipped_optional_unavailable": 0,
        "zip_created": False,
        "download_enabled": download_enabled,
        "enabled": enabled,
        "output_format": "jpg",
        "keep_unzipped_images": keep_unzipped_images,
        "min_images_per_product": min_images_per_product,
        "unzipped_images_kept": False,
    }

    session = requests.Session()
    session.headers.update({
        "User-Agent": settings["user_agent"],
        "Accept": "image/jpeg,image/png,image/webp,image/*,*/*;q=0.8",
    })

    ready_by_template = data.get("ready_by_template") or {}
    for template_key, payloads in sorted(ready_by_template.items()):
        for payload in payloads:
            row = payload.get("row") or {}
            sku = _safe_sku(_text(row.get("merchant_sku") or row.get("image_code") or payload.get("product_key")))
            product_key = payload.get("product_key")
            urls = _split_urls(row.get("image_urls"), int(settings["max_images_per_product"]))
            if not urls:
                stats["products_without_urls"] += 1
                product_summaries.append({
                    "template_key": template_key,
                    "product_key": product_key,
                    "merchant_sku": sku,
                    "status": "below_min_images",
                    "downloaded_images": 0,
                    "source_urls": 0,
                    "required_min_images": min_images_per_product,
                    "optional_skipped": 0,
                    "failed_required": 0,
                })
                continue

            stats["products"] += 1
            product_rows: list[dict[str, Any]] = []
            product_queue_lines: list[str] = []
            product_downloaded_paths: list[Path] = []
            pending_failures: list[dict[str, Any]] = []
            success_count = 0
            output_idx = 0

            for source_idx, url in enumerate(urls, 1):
                stats["source_urls_seen"] += 1
                status = "queued"
                size_bytes = 0
                detail = "download_disabled"
                final_path: Path | None = None

                # Сохраняем только успешные фото в последовательную нумерацию 01.jpg, 02.jpg...
                # Неуспешные ссылки решаем после обработки всего товара: если минимум фото есть,
                # они становятся optional_skipped и не попадают в manifest/queue.
                target_idx = output_idx + 1
                target_base = images_dir / sku / f"{target_idx:02d}"
                rel_path = f"images/{sku}/{target_idx:02d}.jpg"

                if enabled and download_enabled:
                    status, final_path, size_bytes, detail = _download(
                        session,
                        url,
                        target_base,
                        int(settings["timeout_sec"]),
                        int(settings["retries"]),
                        int(settings["min_bytes"]),
                        int(settings["jpeg_quality"]),
                        int(settings["max_side_px"]),
                    )
                    if final_path is not None:
                        output_idx += 1
                        success_count += 1
                        rel_path = final_path.relative_to(package_dir).as_posix()
                        product_downloaded_paths.append(final_path)
                        product_rows.append({
                            "template_key": template_key,
                            "product_key": product_key,
                            "merchant_sku": sku,
                            "image_index": output_idx,
                            "source_index": source_idx,
                            "source_url": url,
                            "kaspi_image_path": rel_path,
                            "status": status,
                            "size_bytes": size_bytes,
                            "detail": detail,
                        })
                        product_queue_lines.append(f"{rel_path}\t{url}")
                        if status == "downloaded":
                            stats["downloaded"] += 1
                        elif status == "cached":
                            stats["cached"] += 1
                    else:
                        pending_failures.append({
                            "template_key": template_key,
                            "product_key": product_key,
                            "merchant_sku": sku,
                            "source_index": source_idx,
                            "source_url": url,
                            "status": status,
                            "size_bytes": size_bytes,
                            "detail": detail,
                        })
                else:
                    output_idx += 1
                    success_count += 1
                    stats["queued_only"] += 1
                    product_rows.append({
                        "template_key": template_key,
                        "product_key": product_key,
                        "merchant_sku": sku,
                        "image_index": output_idx,
                        "source_index": source_idx,
                        "source_url": url,
                        "kaspi_image_path": rel_path,
                        "status": status,
                        "size_bytes": size_bytes,
                        "detail": detail,
                    })
                    product_queue_lines.append(f"{rel_path}\t{url}")

            if success_count >= min_images_per_product:
                stats["products_image_ok"] += 1
                stats["skipped_optional_unavailable"] += len(pending_failures)
                rows.extend(product_rows)
                queue_lines.extend(product_queue_lines)
                downloaded_paths.extend(product_downloaded_paths)
                stats["urls_total"] += len(product_rows)
                product_summaries.append({
                    "template_key": template_key,
                    "product_key": product_key,
                    "merchant_sku": sku,
                    "status": "ok",
                    "downloaded_images": success_count,
                    "source_urls": len(urls),
                    "required_min_images": min_images_per_product,
                    "optional_skipped": len(pending_failures),
                    "failed_required": 0,
                })
            else:
                stats["products_below_min_images"] += 1
                stats["failed"] += len(pending_failures)
                # Если фото меньше минимума, оставляем failed-ссылки в manifest для понятного аудита.
                for failure in pending_failures:
                    output_idx += 1
                    rel_path = f"images/{sku}/{output_idx:02d}.jpg"
                    product_rows.append({
                        **failure,
                        "image_index": output_idx,
                        "kaspi_image_path": rel_path,
                    })
                rows.extend(product_rows)
                queue_lines.extend(product_queue_lines)
                downloaded_paths.extend(product_downloaded_paths)
                stats["urls_total"] += len(product_rows)
                product_summaries.append({
                    "template_key": template_key,
                    "product_key": product_key,
                    "merchant_sku": sku,
                    "status": "below_min_images",
                    "downloaded_images": success_count,
                    "source_urls": len(urls),
                    "required_min_images": min_images_per_product,
                    "optional_skipped": 0,
                    "failed_required": len(pending_failures),
                })

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "template_key", "product_key", "merchant_sku", "image_index", "source_index", "source_url",
                "kaspi_image_path", "status", "size_bytes", "detail",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    queue_path.write_text("\n".join(queue_lines).rstrip() + ("\n" if queue_lines else ""), encoding="utf-8")

    if enabled and create_zip:
        _write_zip(zip_path, package_dir, downloaded_paths)
        stats["zip_created"] = True
        stats["zip_size_bytes"] = zip_path.stat().st_size if zip_path.exists() else 0
    else:
        stats["zip_size_bytes"] = 0

    stats["unzipped_images_kept"] = _cleanup_unzipped_images(package_dir, keep_unzipped_images, bool(stats["zip_created"]))
    write_json(summary_path, {"meta": stats, "settings": settings, "products": product_summaries})
    return {
        "images_manifest_csv": manifest_path,
        "images_download_queue_txt": queue_path,
        "images_summary_json": summary_path,
        "images_zip": zip_path,
    }
