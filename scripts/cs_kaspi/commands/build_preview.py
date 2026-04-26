from __future__ import annotations
from scripts.cs_kaspi.core.file_paths import ensure_base_dirs, get_path
from scripts.cs_kaspi.core.read_json import read_json
from scripts.cs_kaspi.core.write_json import write_json
from scripts.cs_kaspi.preview.build_preview import run as build_preview_data
from scripts.cs_kaspi.preview.write_preview_yml import run as write_yml
from scripts.cs_kaspi.preview.write_preview_xml import run as write_xml
from scripts.cs_kaspi.preview.write_preview_json import run as write_json_preview
from scripts.cs_kaspi.preview.write_preview_txt import run as write_txt
from scripts.cs_kaspi.preview.write_preview_report import run as build_report

def run() -> dict:
    ensure_base_dirs()
    catalog=read_json(get_path("artifacts_state_dir") / "master_catalog.json", default={"products":[]})
    preview=build_preview_data(catalog)
    preview_dir=get_path("artifacts_preview_dir")
    write_yml(preview_dir / "master_preview.yml", preview)
    write_xml(preview_dir / "master_preview.xml", preview)
    write_json_preview(preview_dir / "master_preview.json", preview)
    write_txt(preview_dir / "master_preview.txt", preview)
    report=build_report(preview)
    write_json(get_path("artifacts_reports_dir") / "preview_report.json", report)
    return preview

if __name__ == "__main__":
    run()
