from __future__ import annotations

import csv
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from scripts.cs_kaspi.core.json_io import write_json
from scripts.cs_kaspi.core.paths import ROOT, path_from_config
from scripts.cs_kaspi.core.time_utils import now_iso
from .common import field_codes, load_template
from .image_package import write_image_manifest


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


def _col_name(index: int) -> str:
    name = ""
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def _cell_xml(row_idx: int, col_idx: int, value: Any) -> str:
    ref = f"{_col_name(col_idx)}{row_idx}"
    text = _text(value)
    if text == "":
        return f'<c r="{ref}"/>'
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(text)}</t></is></c>'


def _rows_xml(rows: list[list[Any]]) -> str:
    parts: list[str] = []
    for row_idx, row in enumerate(rows, 1):
        cells = "".join(_cell_xml(row_idx, col_idx, value) for col_idx, value in enumerate(row, 1))
        parts.append(f'<row r="{row_idx}">{cells}</row>')
    return "".join(parts)


def _write_simple_xlsx(path: Path, sheet_name: str, rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    max_cols = max((len(r) for r in rows), default=1)
    last_cell = f"{_col_name(max_cols)}{max(len(rows), 1)}"
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''
    workbook = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="{escape(sheet_name[:31])}" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''
    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''
    sheet_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <dimension ref="A1:{last_cell}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="3" topLeftCell="A4" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetData>{_rows_xml(rows)}</sheetData>
</worksheet>'''
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:creator>CS-Kaspi</dc:creator><cp:lastModifiedBy>CS-Kaspi</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>'''
    app = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>CS-Kaspi</Application>
</Properties>'''

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/styles.xml", styles)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        zf.writestr("docProps/core.xml", core)
        zf.writestr("docProps/app.xml", app)


def _template_header_rows(template: dict[str, Any]) -> list[list[Any]]:
    fields = template.get("fields", []) or []
    return [
        [field.get("raw_rule") or "" for field in fields],
        [field.get("code") or "" for field in fields],
        [field.get("name_ru") or field.get("code") or "" for field in fields],
    ]


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


def _write_template_xlsx(path: Path, template_key: str, payloads: list[dict[str, Any]]) -> None:
    template = load_template(template_key)
    headers = field_codes(template)
    rows = _template_header_rows(template)
    for payload in payloads:
        row = payload.get("row") or {}
        rows.append([_text(row.get(code)) for code in headers])
    _write_simple_xlsx(path, "attributes", rows)


def _write_audit_txt(path: Path, data: dict[str, Any]) -> None:
    meta = data.get("meta", {}) or {}
    lines = [
        "CS-Kaspi Kaspi template export audit",
        f"built_at: {meta.get('built_at') or now_iso()}",
        "note: template_ready можно переносить в XLSX/CSV шаблон Kaspi; template_blocked нельзя загружать без исправления обязательных полей.",
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
    xlsx_files: dict[str, Path] = {}
    for template_key, rows in sorted(ready_by_template.items()):
        csv_path = out_dir / f"kaspi_template_ready_{template_key}.csv"
        xlsx_path = out_dir / f"kaspi_template_ready_{template_key}.xlsx"
        _write_template_csv(csv_path, template_key, rows)
        _write_template_xlsx(xlsx_path, template_key, rows)
        csv_files[f"template_ready_csv_{template_key}"] = csv_path
        xlsx_files[f"template_ready_xlsx_{template_key}"] = xlsx_path

    write_json(files["template_audit_json"], data)
    write_json(files["template_blocked_json"], {"meta": data.get("meta", {}), "products": data.get("blocked", [])})
    _write_audit_txt(files["template_audit_txt"], data)

    image_files = write_image_manifest(data)
    all_files = {**files, **csv_files, **xlsx_files, **image_files}
    return {key: _rel(path) for key, path in all_files.items()}
