from __future__ import annotations

import re
from urllib.parse import unquote

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def normalize_spaces(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def transliterate(value: str | None) -> str:
    value = unquote(value or "").lower().replace("ё", "е")
    return "".join(TRANSLIT.get(ch, ch) for ch in value)


def slugify_ascii(value: str | None) -> str:
    text = transliterate(value)
    text = text.replace("wifi", " wifi ")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def limit_text(value: str, max_len: int) -> str:
    value = normalize_spaces(value)
    if len(value) <= max_len:
        return value
    return value[: max_len - 1].rstrip() + "…"


def clean_html_text(value: str | None) -> str:
    return normalize_spaces(value).replace("<", "").replace(">", "")
