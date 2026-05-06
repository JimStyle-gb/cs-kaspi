from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ALMATY_TZ = ZoneInfo("Asia/Almaty")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_almaty_iso() -> str:
    return datetime.now(ALMATY_TZ).isoformat()
