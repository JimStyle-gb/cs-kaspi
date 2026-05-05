from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from scripts.cs_kaspi.core.json_io import write_json
from scripts.cs_kaspi.core.paths import ROOT, path_from_config
from scripts.cs_kaspi.core.time_utils import now_iso
from .common import field_codes, load_template


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except Exception:
        return path.as_posix()


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return str(value)


def _write_template_csv(path: Path, template_key: str, payloads: list[dict[str, Any]]) -> None:
    template = load_template(template_key)
    headers = field_codes(template)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for payload in payloads:
            row = payload.get("row") or {}
            writer.writerow({code: _text(row.get(code)) for code in headers})


def _write_audit_txt(path: Path, data: dict[str, Any]) -> None:
    meta = data.get("meta", {}) or {}
    lines = [
        "CS-Kaspi Kaspi template export audit",
        f"built_at: {meta.get('built_at') or now_iso()}",
        "note: template_ready можно переносить в CSV/XLSM шаблон Kaspi; template_blocked нельзя загружать без исправления обязательных полей.",
        "",
        f"commercial_candidates: {meta.get('commercial_candidates')}",
        f"template_ready: {meta.get('template_ready')}",
        f"template_blocked: {meta.get('template_blocked')}",
        f"by_template: {meta.get('by_template')}",
        "",
    ]
    blocked = data.get("blocked") or []
    lines.append("blocked products:")
    if not blocked:
        lines.append("  none")
    for item in blocked[:80]:
        lines.append(f"  - {item.get('product_key')} | {item.get('template_key')} | {item.get('kaspi_title')}")
        lines.append(f"    errors: {', '.join(item.get('errors') or [])}")
        if item.get("market_url"):
            lines.append(f"    wb: {item.get('market_url')}")
    if len(blocked) > 80:
        lines.append(f"  ... and {len(blocked) - 80} more")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_template_exports(data: dict[str, Any]) -> dict[str, str]:
    out_dir = path_from_config("artifacts_exports_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {
        "template_audit_json": out_dir / "kaspi_template_audit.json",
        "template_audit_txt": out_dir / "kaspi_template_audit.txt",
        "template_blocked_json": out_dir / "kaspi_template_blocked_products.json",
    }
    ready_by_template = data.get("ready_by_template") or {}
    csv_files: dict[str, Path] = {}
    for template_key, rows in sorted(ready_by_template.items()):
        path = out_dir / f"kaspi_template_ready_{template_key}.csv"
        _write_template_csv(path, template_key, rows)
        csv_files[f"template_ready_csv_{template_key}"] = path

    write_json(files["template_audit_json"], data)
    write_json(files["template_blocked_json"], {"meta": data.get("meta", {}), "products": data.get("blocked", [])})
    _write_audit_txt(files["template_audit_txt"], data)

    all_files = {**files, **csv_files}
    return {key: _rel(path) for key, path in all_files.items()}
