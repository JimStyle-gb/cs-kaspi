from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Any

from scripts.cs_kaspi.core.text_utils import normalize_spaces
from scripts.cs_kaspi.core.time_utils import ALMATY_TZ

_PRICE_RE = re.compile(r"(?P<num>\d[\d\s\u2009\u202f]{2,})(?:\s?₸|\s?тг|\s?kzt|\s?₽|\s?руб)?", re.IGNORECASE)
_KZT_RE = re.compile(r"(?:₸|тг|kzt)", re.IGNORECASE)
_RUB_RE = re.compile(r"(?:₽|руб|rub)", re.IGNORECASE)
_MONTHLY_RE = re.compile(r"(?:мес|месяц|x\s*\d+|×\s*\d+)", re.IGNORECASE)
_STOCK_RE = re.compile(r"(?P<n>\d+)\s*шт\s+остал(?:ось|ись)?|остал(?:ось|ись)?\s+(?P<n2>\d+)\s*шт", re.IGNORECASE)
_DATE_RE = re.compile(r"(?P<day>\d{1,2})\s+(?P<month>января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)", re.IGNORECASE)
_MODEL_CODE_RE = re.compile(r"\b(?:dk|дк|aa|bl|kf)[\s\-/]*\d{2,5}\b", re.IGNORECASE)
_LETTER_RE = re.compile(r"[A-Za-zА-Яа-яЁё]")

MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}

NOISE_LINES = (
    "в корзину", "добавить", "рассрочка", "мес", "скидка", "осталось", "остались", "доставка",
    "завтра", "сегодня", "послезавтра", "отзыв", "рейтинг", "распродажа",
    "хорошая цена", "с wb кошельком", "wb кошелек", "кошельком",
)


def _clean_text(value: Any) -> str:
    return normalize_spaces(html.unescape(str(value or "").replace("\xa0", " ")))


def _num(text: str) -> int | None:
    digits = re.sub(r"\D+", "", text or "")
    if not digits:
        return None
    value = int(digits)
    return value if value > 0 else None


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value > 0:
        return int(value)
    if isinstance(value, str):
        return _num(value)
    return None


def detect_currency(text: str) -> str | None:
    raw = html.unescape(text or "")
    if _KZT_RE.search(raw):
        return "KZT"
    if _RUB_RE.search(raw):
        return "RUB"
    return None


def _line_price_candidate(line: str, *, required_currency: str | None = None) -> int | None:
    clean = _clean_text(line)
    if not clean:
        return None
    lower = clean.lower()
    if _MONTHLY_RE.search(lower):
        return None

    if required_currency == "KZT" and not _KZT_RE.search(clean):
        return None
    if required_currency == "RUB" and not _RUB_RE.search(clean):
        return None

    has_any_currency = bool(_KZT_RE.search(clean) or _RUB_RE.search(clean))
    if not has_any_currency:
        if _LETTER_RE.search(clean):
            return None
        if not re.fullmatch(r"[\d\s\u2009\u202f]+", clean):
            return None

    values: list[int] = []
    for match in _PRICE_RE.finditer(clean):
        value = _num(match.group("num"))
        if value and value >= 300:
            values.append(value)
    if not values:
        return None
    return min(values)


def extract_price(text: str, *, required_currency: str | None = None) -> int | None:
    raw = html.unescape(text or "")
    values: list[int] = []

    for line in raw.splitlines():
        candidate = _line_price_candidate(line, required_currency=required_currency)
        if candidate:
            values.append(candidate)

    if values:
        return min(values)

    for match in _PRICE_RE.finditer(raw):
        value = _num(match.group("num"))
        if not value or value < 300:
            continue
        ctx = (raw[max(0, match.start() - 24):match.end() + 32] or "").lower()
        if _MONTHLY_RE.search(ctx):
            continue
        if required_currency == "KZT" and not _KZT_RE.search(ctx):
            continue
        if required_currency == "RUB" and not _RUB_RE.search(ctx):
            continue
        if required_currency is None and not (_KZT_RE.search(ctx) or _RUB_RE.search(ctx)):
            continue
        if _MODEL_CODE_RE.search(ctx):
            continue
        values.append(value)
    return min(values) if values else None


def extract_stock(text: str) -> int | None:
    match = _STOCK_RE.search(html.unescape(text or ""))
    if not match:
        return None
    return int(match.group("n") or match.group("n2"))


def extract_eta_text(text: str) -> str | None:
    lower = html.unescape(text or "").lower()
    if "сегодня" in lower:
        return "сегодня"
    if "послезавтра" in lower:
        return "послезавтра"
    if "завтра" in lower:
        return "завтра"
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
    clean = _clean_text(line)
    lower = clean.lower()
    if len(clean) < 10:
        return -10
    if any(x in lower for x in NOISE_LINES):
        return -20
    score = len(clean)
    if "demiand" in lower or "демианд" in lower:
        score += 70
    if any(x in lower for x in ("аэрогр", "кофевар", "блендер", "суповар", "печ", "шампур", "аксессуар", "форма", "решет", "решёт", "корзин")):
        score += 30
    return score


def extract_title(raw: dict[str, Any]) -> str:
    # Explicit source title/link text must win. Container text can contain neighbouring WB cards.
    for key in ("title", "link_text", "aria_label", "image_alt"):
        value = _clean_text(raw.get(key))
        if value:
            return value
    candidates: list[str] = []
    for line in str(raw.get("container_text") or "").splitlines():
        clean = _clean_text(line)
        if clean:
            candidates.append(clean)
    if not candidates:
        return ""
    return sorted(candidates, key=_line_score, reverse=True)[0]


def normalize_card(raw: dict[str, Any]) -> dict[str, Any]:
    raw_text = html.unescape(str(raw.get("container_text") or ""))
    text = _clean_text(raw_text)
    title = extract_title(raw)
    raw_currency = str(raw.get("price_currency") or "").upper() or None
    text_currency = raw_currency or detect_currency(raw_text)
    explicit_price = _int_or_none(raw.get("price"))

    # If exact card HTML gives KZT, prefer it over WB network numeric price.
    # GitHub can see RUB because of runner geo; RUB must not silently become Kaspi KZT.
    kzt_price = extract_price(raw_text, required_currency="KZT") if text_currency == "KZT" else None
    rub_price = extract_price(raw_text, required_currency="RUB") if text_currency == "RUB" else None
    if kzt_price:
        price = kzt_price
        price_currency = "KZT"
    elif text_currency == "RUB":
        price = rub_price or explicit_price
        price_currency = "RUB"
    else:
        price = explicit_price or extract_price(raw_text)
        price_currency = None

    explicit_stock = _int_or_none(raw.get("stock"))
    stock = explicit_stock if explicit_stock is not None else extract_stock(raw_text)
    eta_text = _clean_text(raw.get("eta_text")) or extract_eta_text(raw_text)
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
        "brand": _clean_text(raw.get("brand")),
        "title": title,
        "url": url,
        "image": raw.get("image"),
        "price": price,
        "price_currency": price_currency,
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
