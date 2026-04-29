from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from scripts.cs_kaspi.core.text_utils import normalize_spaces
from scripts.cs_kaspi.core.time_utils import ALMATY_TZ

_PRICE_RE = re.compile(r"(?P<num>\d[\d \u00a0]{2,})(?:\s?₸|\s?тг|\s?kzt)?", re.IGNORECASE)
_MONTHLY_RE = re.compile(r"(?:мес|месяц|x\s*\d+|×\s*\d+)", re.IGNORECASE)
_STOCK_RE = re.compile(r"остал(?:ось|ись)?\s+(?P<n>\d+)\s*шт", re.IGNORECASE)
_DATE_RE = re.compile(r"(?P<day>\d{1,2})\s+(?P<month>января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)", re.IGNORECASE)

MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}

NOISE_LINES = (
    "в корзину", "добавить", "рассрочка", "мес", "скидка", "осталось", "доставка",
    "завтра", "сегодня", "послезавтра", "₸", "тг", "отзыв", "рейтинг",
)

_MODEL_CODE_RE = re.compile(r"(?:^|\b)(?:dk|aa|kf|dm|duos)[\s\-_/]*\d{2,6}(?:\b|$)", re.IGNORECASE)
_PRICE_LINE_RE = re.compile(r"^\s*(?:от\s*)?(?P<num>\d[\d \u00a0]{3,})(?:\s*(?:₸|тг|kzt))?\s*$", re.IGNORECASE)
_PRICE_WITH_CURRENCY_RE = re.compile(r"(?P<num>\d[\d \u00a0]{3,})\s*(?:₸|тг|kzt)\b", re.IGNORECASE)


def _num(text: str) -> int | None:
    digits = re.sub(r"\D+", "", text or "")
    if not digits:
        return None
    value = int(digits)
    return value if value > 0 else None


def _looks_like_model_code_context(text: str, start: int, end: int) -> bool:
    ctx = (text[max(0, start - 18):min(len(text), end + 18)] or "")
    return bool(_MODEL_CODE_RE.search(ctx))


def _line_price_candidates(text: str) -> list[int]:
    values: list[int] = []
    for raw_line in (text or "").splitlines():
        line = normalize_spaces(raw_line)
        if not line:
            continue
        lower = line.lower()
        if _MONTHLY_RE.search(lower):
            continue
        if _MODEL_CODE_RE.search(line):
            continue
        match = _PRICE_LINE_RE.match(line)
        if not match:
            continue
        value = _num(match.group("num"))
        if value and 1000 <= value <= 2_000_000:
            values.append(value)
    return values


def extract_price(text: str) -> int | None:
    raw_text = str(text or "")

    # WB API cards often arrive as separate lines: brand / title with DK-2500 / price / reviews.
    # Prefer a standalone price line so model codes are not concatenated with price.
    line_values = _line_price_candidates(raw_text)
    if line_values:
        return min(line_values)

    currency_values: list[int] = []
    for match in _PRICE_WITH_CURRENCY_RE.finditer(raw_text):
        value = _num(match.group("num"))
        if not value or value < 1000:
            continue
        ctx = (raw_text[max(0, match.start() - 18):match.end() + 24] or "").lower()
        if _MONTHLY_RE.search(ctx):
            continue
        if _looks_like_model_code_context(raw_text, match.start(), match.end()):
            continue
        if value <= 2_000_000:
            currency_values.append(value)
    if currency_values:
        return min(currency_values)

    values: list[int] = []
    compact_text = normalize_spaces(raw_text)
    for match in _PRICE_RE.finditer(compact_text):
        value = _num(match.group("num"))
        if not value or value < 1000:
            continue
        ctx = (compact_text[max(0, match.start() - 18):match.end() + 24] or "").lower()
        if _MONTHLY_RE.search(ctx):
            continue
        if _looks_like_model_code_context(compact_text, match.start(), match.end()):
            continue
        if value <= 2_000_000:
            values.append(value)
    if not values:
        return None
    return min(values)


def extract_stock(text: str) -> int | None:
    match = _STOCK_RE.search(text or "")
    if not match:
        return None
    return int(match.group("n"))


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
    if any(x in lower for x in ("аэрогр", "кофевар", "блендер", "печ", "шампур", "аксессуар", "форма", "решет", "корзин")):
        score += 30
    return score


def extract_title(raw: dict[str, Any]) -> str:
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
    raw_text = str(raw.get("container_text") or "")
    text = normalize_spaces(raw_text)
    title = extract_title(raw)
    price = extract_price(raw_text)
    stock = extract_stock(raw_text)
    eta_text = extract_eta_text(raw_text)
    return {
        "source": raw.get("source"),
        "seed_key": raw.get("seed_key"),
        "seed_url": raw.get("seed_url"),
        "market_id": raw.get("href"),
        "title": title,
        "url": raw.get("href"),
        "image": raw.get("image"),
        "price": price,
        "available": bool(price) if stock is None else stock > 0,
        "stock": stock if stock is not None else (1 if price else 0),
        "eta_text": eta_text,
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
