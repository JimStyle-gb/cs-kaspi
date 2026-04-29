from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from scripts.cs_kaspi.core.text_utils import normalize_spaces
from scripts.cs_kaspi.core.time_utils import ALMATY_TZ

_PRICE_RE = re.compile(r"(?P<num>\d[\d\s\u2009\u202f]{2,})(?:\s?₸|\s?тг|\s?kzt)?", re.IGNORECASE)
_MONTHLY_RE = re.compile(r"(?:мес|месяц|x\s*\d+|×\s*\d+)", re.IGNORECASE)
_STOCK_RE = re.compile(r"(?P<n>\d+)\s*шт\s+остал(?:ось|ись)?|остал(?:ось|ись)?\s+(?P<n2>\d+)\s*шт", re.IGNORECASE)
_DATE_RE = re.compile(r"(?P<day>\d{1,2})\s+(?P<month>января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)", re.IGNORECASE)

MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}

NOISE_LINES = (
    "в корзину", "добавить", "рассрочка", "мес", "скидка", "осталось", "остались", "доставка",
    "завтра", "сегодня", "послезавтра", "₸", "тг", "отзыв", "рейтинг",
)


def _num(text: str) -> int | None:
    digits = re.sub(r"\D+", "", text or "")
    if not digits:
        return None
    value = int(digits)
    return value if value > 0 else None


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str):
        return _num(value)
    return None


def extract_price(text: str) -> int | None:
    values: list[tuple[int, str]] = []
    for match in _PRICE_RE.finditer(text or ""):
        value = _num(match.group("num"))
        if not value or value < 1000:
            continue
        ctx = (text[max(0, match.start() - 18):match.end() + 24] or "").lower()
        if _MONTHLY_RE.search(ctx):
            continue
        values.append((value, ctx))
    if not values:
        return None
    return min(value for value, _ in values)


def extract_stock(text: str) -> int | None:
    match = _STOCK_RE.search(text or "")
    if not match:
        return None
    return int(match.group("n") or match.group("n2"))


def extract_eta_text(text: str) -> str | None:
    lower = (text or "").lower()
    if "сегодня" in lower:
        return "сегодня"
    if "завтра" in lower:
        return "завтра"
    if "послезавтра" in lower:
        return "послезавтра"
    match = _DATE_RE.search(lower)
    if match:
        return f"{match.group('day')} {match.group('month')}"
    return None


def eta_to_days(eta_text: str | None) -> int | None:
    if not eta_text:
        return None
    now = datetime.now(ALMATY_TZ).date()
    lower = eta_text.lower()
    if lower == "сегодня":
        return 0
    if lower == "завтра":
        return 1
    if lower == "послезавтра":
        return 2
    match = _DATE_RE.search(lower)
    if not match:
        return None
    day = int(match.group("day"))
    month = MONTHS[match.group("month")]
    target = now.replace(month=month, day=day)
    if target < now:
        target = target.replace(year=target.year + 1)
    return max(0, (target - now).days)


def _line_score(line: str) -> int:
    clean = normalize_spaces(line)
    lower = clean.lower()
    if len(clean) < 10:
        return -10
    if any(x in lower for x in NOISE_LINES):
        return -20
    score = len(clean)
    if "demiand" in lower:
        score += 70
    if any(x in lower for x in ("аэрогр", "кофевар", "блендер", "печ", "шампур", "аксессуар")):
        score += 30
    return score


def extract_title(raw: dict[str, Any]) -> str:
    explicit = normalize_spaces(str(raw.get("title") or ""))
    if explicit:
        return explicit
    candidates: list[str] = []
    for key in ("aria_label", "image_alt", "link_text"):
        value = normalize_spaces(str(raw.get(key) or ""))
        if value:
            candidates.append(value)
    for line in str(raw.get("container_text") or "").splitlines():
        clean = normalize_spaces(line)
        if clean:
            candidates.append(clean)
    if not candidates:
        return ""
    return sorted(candidates, key=_line_score, reverse=True)[0]


def normalize_card(raw: dict[str, Any]) -> dict[str, Any]:
    text = normalize_spaces(str(raw.get("container_text") or ""))
    title = extract_title(raw)
    explicit_price = _int_or_none(raw.get("price"))
    price = explicit_price or extract_price(text)
    explicit_stock = _int_or_none(raw.get("stock"))
    stock = explicit_stock if explicit_stock is not None else extract_stock(text)
    eta_text = normalize_spaces(str(raw.get("eta_text") or "")) or extract_eta_text(text)
    url = raw.get("url") or raw.get("href")
    market_id = raw.get("market_id") or url
    available = raw.get("available")
    if available is None:
        available = bool(price) if stock is None else stock > 0
    return {
        "source": raw.get("source"),
        "seed_key": raw.get("seed_key"),
        "seed_url": raw.get("seed_url"),
        "market_id": market_id,
        "title": title,
        "url": url,
        "image": raw.get("image"),
        "price": price,
        "old_price": _int_or_none(raw.get("old_price")),
        "available": bool(available),
        "stock": stock if stock is not None else (1 if price else 0),
        "eta_text": eta_text or None,
        "lead_time_days": eta_to_days(eta_text),
        "raw_text": text[:2000],
        "raw": raw,
    }


def normalize_cards(raw_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for raw in raw_cards:
        row = normalize_card(raw)
        key = str(row.get("url") or row.get("market_id") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return rows
