from __future__ import annotations

from collections import Counter
from typing import Any

from scripts.cs_kaspi.core.json_io import read_json, write_json
from scripts.cs_kaspi.core.paths import ensure_runtime_dirs, path_from_config
from scripts.cs_kaspi.core.time_utils import now_iso


def _txt_report(report: dict[str, Any]) -> str:
    lines = [
        "CS-Kaspi check report",
        f"checked_at: {report.get('checked_at')}",
        f"total_products: {report.get('total_products')}",
        f"critical_count: {report.get('critical_count')}",
        f"cosmetic_count: {report.get('cosmetic_count')}",
        f"missing_model_specs: {report.get('missing_model_specs')}",
        f"missing_price: {report.get('missing_price')}",
        f"wait_market_data: {report.get('wait_market_data')}",
        f"with_market_data: {report.get('with_market_data')}",
        f"market_sellable: {report.get('market_sellable')}",
        f"ready_for_kaspi: {report.get('ready_for_kaspi')}",
        "",
        "categories:",
    ]
    for key, value in report.get("categories", {}).items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("market_sources:")
    for key, value in report.get("market_sources", {}).items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("problems:")
    for problem in report.get("problems", [])[:300]:
        lines.append(f"  [{problem.get('level')}] {problem.get('product_key')}: {problem.get('message')}")
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    ensure_runtime_dirs()
    state_dir = path_from_config("artifacts_state_dir")
    reports_dir = path_from_config("artifacts_reports_dir")
    catalog = read_json(state_dir / "master_catalog.json", required=True)
    products = catalog.get("products", [])
    validation = catalog.get("validation", {}) or {}
    problems = list(validation.get("problems", []))

    for product in products:
        key = product.get("product_key")
        kaspi = product.get("kaspi_policy", {}) or {}
        if not kaspi.get("kaspi_title"):
            problems.append({"level": "critical", "product_key": key, "message": "missing kaspi_title"})
        if not kaspi.get("kaspi_description"):
            problems.append({"level": "critical", "product_key": key, "message": "missing kaspi_description"})
        if not kaspi.get("kaspi_attributes"):
            problems.append({"level": "critical", "product_key": key, "message": "missing kaspi_attributes"})
        if not kaspi.get("kaspi_images"):
            problems.append({"level": "cosmetic", "product_key": key, "message": "missing kaspi_images"})
        if len(kaspi.get("kaspi_images") or []) > 10:
            problems.append({"level": "critical", "product_key": key, "message": "kaspi images over limit 10"})

    report = {
        "checked_at": now_iso(),
        "total_products": len(products),
        "critical_count": sum(1 for p in problems if p.get("level") == "critical"),
        "cosmetic_count": sum(1 for p in problems if p.get("level") == "cosmetic"),
        "categories": dict(Counter(p.get("category_key") for p in products)),
        "suppliers": dict(Counter(p.get("supplier_key") for p in products)),
        "market_sources": dict(Counter(p.get("market", {}).get("market_price_source") for p in products if p.get("market", {}).get("market_price_source"))),
        "missing_model_specs": sum(1 for p in products if not p.get("model_specs", {}).get("exists")),
        "missing_price": sum(1 for p in products if p.get("kaspi_policy", {}).get("kaspi_price") is None),
        "wait_market_data": sum(1 for p in products if p.get("status", {}).get("action_status") == "wait_market_data"),
        "with_market_data": sum(1 for p in products if p.get("market", {}).get("sources")),
        "market_sellable": sum(1 for p in products if p.get("market", {}).get("sellable") is True),
        "ready_for_kaspi": sum(1 for p in products if p.get("status", {}).get("action_status") == "ready_for_create_or_update"),
        "problems": problems,
    }
    write_json(reports_dir / "check_project_report.json", report)
    (reports_dir / "check_project_report.txt").write_text(_txt_report(report), encoding="utf-8")
    if report["critical_count"]:
        raise RuntimeError(f"Check_Project found critical issues: {report['critical_count']}. See artifacts/reports/check_project_report.txt")
    return report


if __name__ == "__main__":
    run()
