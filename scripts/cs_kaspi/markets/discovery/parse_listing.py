from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Any

from scripts.cs_kaspi.core.text_utils import normalize_spaces
from scripts.cs_kaspi.core.time_utils import ALMATY_TZ

_PRICE_RE = re.compile(r"(?P<num>\d[\d\s\u00a0\u2009\u202f]{2,})(?:\s?₸|\s?тг|\s?kzt|\s?₽|\s?руб)?", re.IGNORECASE)
_CURRENCY_PRICE_RE = re.compile(r"(?P<num>\d[\d\s\u00a0\u2009\u202f]{2,})\s?(?P<cur>₸|тг|kzt|₽|руб|rub)", re.IGNORECASE)
_KZT_RE = re.compile(r"(?:₸|тг|kzt)", re.IGNORECASE)
_RUB_RE = re.compile(r"(?:₽|руб|rub)", re.IGNORECASE)
_MONTHLY_RE = re.compile(r"(?:мес|месяц|x\s*\d+|×\s*\d+)", re.IGNORECASE)
_STOCK_RE = re.compile(r"(?P<n>\d+)\s*шт\s+остал(?:ось|ись)?|остал(?:ось|ись)?\s+(?P<n2>\d+)\s*шт", re.IGNORECASE)
_DATE_RE = re.compile(r"(?P<day>\d{1,2})\s+(?P<month>января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)", re.IGNORECASE)
_MODEL_CODE_RE = re.compile(r"\b(?:dk|дк|aa|bl|kf)[\s\-/]*\d{2,5}\b", re.IGNORECASE)
_LETTER_RE = re.compile(r"[A-Za-zА-Яа-яЁё]")
_PRODUCT_TITLE_RE = re.compile(
    r"(?:demiand|демианд|lumme|аэрогр|блендер|суповар|кофевар|мини\s*печ|решет|решёт|шампур|корзин|форма|пергамент|чаша)",
    re.IGNORECASE,
)

MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}

NOISE_LINES = (
    "в корзину", "добавить", "рассрочка", "мес", "скидка", "осталось", "остались", "доставка",
    "завтра", "сегодня", "послезавтра", "отзыв", "рейтинг", "распродажа",
    "хорошая цена", "с wb кошельком", "wb кошелек", "кошельком", "быстрый просмотр",
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

    currency_values: list[int] = []
    for match in _CURRENCY_PRICE_RE.finditer(clean):
        cur = match.group("cur") or ""
        if required_currency == "KZT" and not _KZT_RE.search(cur):
            continue
        if required_currency == "RUB" and not _RUB_RE.search(cur):
            continue
        value = _num(match.group("num"))
        if value and value >= 300:
            currency_values.append(value)
    if currency_values:
        return min(currency_values)

    if "оцен" in lower or "рейтинг" in lower:
        return None

    has_any_currency = bool(_KZT_RE.search(clean) or _RUB_RE.search(clean))
    if not has_any_currency:
        if _LETTER_RE.search(clean):
            return None
        if not re.fullmatch(r"[\d\s\u00a0\u2009\u202f]+", clean):
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


def _norm_key(text: str) -> str:
    text = _clean_text(text).lower().replace("ё", "е")
    text = re.sub(r"\bdemiand\b|демианд", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[^a-z0-9а-я]+", " ", text, flags=re.IGNORECASE)
    return normalize_spaces(text)


def _important_tokens(text: str) -> set[str]:
    stop = {
        "demiand", "аэрогриль", "аэрогр", "блендер", "суповарка", "нагревом", "решетка", "решётка",
        "шампурами", "шампур", "для", "черный", "черная", "чёрный", "чёрная", "белый", "белая",
        "с", "и", "в", "л", "wi", "fi", "wifi", "электрическая", "мини", "печь",
    }
    out: set[str] = set()
    for token in _norm_key(text).split():
        if len(token) >= 3 and token not in stop:
            out.add(token)
    return out


def _same_title_line(line: str, title: str) -> bool:
    line_key = _norm_key(line)
    title_key = _norm_key(title)
    if not line_key or not title_key:
        return False
    if line_key == title_key or title_key in line_key or line_key in title_key:
        return True
    line_tokens = _important_tokens(line_key)
    title_tokens = _important_tokens(title_key)
    if not title_tokens or not line_tokens:
        return False
    overlap = line_tokens & title_tokens
    return len(overlap) >= max(2, min(4, len(title_tokens)))


def _is_product_title_line(line: str) -> bool:
    clean = _clean_text(line)
    if len(clean) < 12:
        return False
    low = clean.lower()
    if any(noise in low for noise in NOISE_LINES):
        return False
    return bool(_PRODUCT_TITLE_RE.search(clean))


def _title_indexes(lines: list[str], title: str) -> list[int]:
    return [idx for idx, line in enumerate(lines) if _same_title_line(line, title)]


def _price_contexts_before_title(text: str, title: str) -> list[str]:
    """Return only the lines before the matching title.

    In WB listing cards the visible sale price is placed before the title. Lines after the title can already
    belong to the next card, so they must not be used for price extraction.
    """
    lines = [_clean_text(line) for line in html.unescape(text or "").splitlines()]
    lines = [line for line in lines if line]
    blocks: list[str] = []
    for idx in _title_indexes(lines, title):
        start = idx
        for pos in range(idx - 1, max(-1, idx - 14), -1):
            if _is_product_title_line(lines[pos]) and not _same_title_line(lines[pos], title):
                break
            start = pos
        block = "\n".join(lines[start:idx + 1])
        if block and block not in blocks:
            blocks.append(block)
    return blocks


def _eta_contexts_after_title(text: str, title: str) -> list[str]:
    lines = [_clean_text(line) for line in html.unescape(text or "").splitlines()]
    lines = [line for line in lines if line]
    blocks: list[str] = []
    for idx in _title_indexes(lines, title):
        end = idx
        for pos in range(idx + 1, min(len(lines), idx + 7)):
            if _is_product_title_line(lines[pos]) and not _same_title_line(lines[pos], title):
                break
            end = pos
            if extract_eta_text(lines[pos]):
                break
        block = "\n".join(lines[idx:end + 1])
        if block and block not in blocks:
            blocks.append(block)
    return blocks


def _extract_scoped_price(text: str, title: str, currency: str | None) -> int | None:
    values: list[int] = []
    for block in _price_contexts_before_title(text, title):
        value = extract_price(block, required_currency=currency)
        if value:
            values.append(value)
    return min(values) if values else None


def _extract_scoped_eta(text: str, title: str) -> str | None:
    values: list[str] = []
    for block in _eta_contexts_after_title(text, title):
        eta = extract_eta_text(block)
        if eta:
            values.append(eta)
    return values[0] if values else None

def normalize_card(raw: dict[str, Any]) -> dict[str, Any]:
    raw_text = html.unescape(str(raw.get("container_text") or ""))
    text = _clean_text(raw_text)
    title = extract_title(raw)
    raw_currency = str(raw.get("price_currency") or "").upper() or None
    text_currency = raw_currency or detect_currency(raw_text)
    explicit_price = _int_or_none(raw.get("price"))

    # Prefer only a KZT price that is scoped to this product title. Do not take the minimum price from the
    # full WB container because it can contain neighbouring cards.
    kzt_price = _extract_scoped_price(raw_text, title, "KZT") if text_currency == "KZT" else None
    rub_price = _extract_scoped_price(raw_text, title, "RUB") if text_currency == "RUB" else None
    if text_currency == "KZT" and explicit_price:
        # For WB API cards the numeric price can be trusted only after listing_browser stamped the card
        # with page-level KZT. The card text itself may not contain the ₸ symbol.
        price = explicit_price
        price_currency = "KZT"
    elif kzt_price:
        price = kzt_price
        price_currency = "KZT"
    elif text_currency == "RUB":
        price = rub_price or explicit_price
        price_currency = "RUB"
    else:
        # Network/API numeric price has no trusted currency. Keep it for debug/review only.
        price = explicit_price or _extract_scoped_price(raw_text, title, None) or extract_price(raw_text)
        price_currency = None

    explicit_stock = _int_or_none(raw.get("stock"))
    stock = explicit_stock if explicit_stock is not None else extract_stock(raw_text)
    eta_text = _clean_text(raw.get("eta_text")) or _extract_scoped_eta(raw_text, title) or extract_eta_text(raw_text)
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
