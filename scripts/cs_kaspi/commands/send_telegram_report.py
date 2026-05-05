from __future__ import annotations

import os
from typing import Any

import requests

from scripts.cs_kaspi.core.paths import path_from_config
from scripts.cs_kaspi.core.time_utils import now_iso


def run() -> dict[str, Any]:
    reports_dir = path_from_config("artifacts_reports_dir")
    text_path = reports_dir / "telegram_summary.txt"
    status_path = reports_dir / "telegram_send_status.txt"
    text = text_path.read_text(encoding="utf-8") if text_path.exists() else "CS-Kaspi: telegram summary not found"
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        status = {"sent": False, "reason": "telegram_env_missing", "checked_at": now_iso()}
        status_path.write_text(str(status) + "\n", encoding="utf-8")
        return status
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text[:3900]},
            timeout=20,
        )
        status = {"sent": resp.ok, "status_code": resp.status_code, "checked_at": now_iso()}
        if not resp.ok:
            status["response"] = resp.text[:500]
    except Exception as exc:
        status = {"sent": False, "error": str(exc), "checked_at": now_iso()}
    status_path.write_text(str(status) + "\n", encoding="utf-8")
    return status


if __name__ == "__main__":
    run()
