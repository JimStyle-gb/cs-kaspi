from __future__ import annotations

import html as html_lib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from scripts.cs_kaspi.core.paths import path_from_config

from .seed_config import browser_cfg, discovery_cfg

_WB_HOST_MARKERS = ("wildberries.", "wb.ru", "wbbasket.", "catalog.wb")
_TEXT_KEYS = (
    "title", "name", "text", "label", "caption", "subtitle", "brand", "brandName", "seller",
    "delivery", "price", "finalPrice", "cardPrice", "salePrice", "marketingLabel", "description",
)
_IMAGE_KEYS = ("image", "imageUrl", "img", "src", "cover", "picture", "thumbnail", "preview")
_WB_TYPE_HINTS = (
    "аэрогр", "кофевар", "блендер", "суповар", "печ", "шампур", "аксессуар", "форма",
    "решет", "решёт", "корзин", "чаша", "пергамент", "стаканчик",
)
_BLOCKED_MARKERS = (
    "почти готово", "подозрительная активность", "captcha", "капча", "captcha-support@rwb.ru",
    "доступ ограничен", "пожалуйста, подождите", "verify", "robot",
)
_HREF_RE = re.compile(r'href=["\'](?P<href>[^"\']{0,500}/catalog/\d+/detail[^"\']{0,220})["\']', re.IGNORECASE)
_ANY_URL_RE = re.compile(r'["\'](?P<href>(?:https?:)?//[^"\']{0,160}/catalog/\d+/detail[^"\']{0,220}|/catalog/\d+/detail[^"\']{0,220})["\']', re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def _slug(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9а-яё_-]+", "_", text, flags=re.IGNORECASE)
    return text.strip("_")[:80] or "seed"


def _debug_dir() -> Path | None:
    try:
        path = path_from_config("artifacts_market_discovery_dir") / "debug"
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception:
        return None


def _write_debug(seed_key: Any, name: str, data: str | bytes) -> None:
    out_dir = _debug_dir()
    if not out_dir:
        return
    path = out_dir / f"{_slug(seed_key)}__{name}"
    try:
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data, encoding="utf-8")
    except Exception:
        pass


def _abs_url(seed_url: str, href: str) -> str:
    href = html_lib.unescape((href or "").strip())
    if href.startswith("//"):
        scheme = urlparse(seed_url).scheme or "https"
        return f"{scheme}:{href}"
    return urljoin(seed_url, href)


def _clean_url(url: str) -> str:
    if not url:
        return ""
    # WB product identity is the catalog id. targetUrl/query noise should not split one product.
    match = re.search(r"(https?://[^/]+/catalog/\d+/detail\.aspx|/catalog/\d+/detail\.aspx)", url, flags=re.IGNORECASE)
    return match.group(1) if match else url.split("#", 1)[0]


def _is_wb_product_url(href: str) -> bool:
    href_l = (href or "").lower()
    return "/catalog/" in href_l and "/detail" in href_l


def _same_wb_family(href: str) -> bool:
    try:
        host = urlparse(href).netloc.lower().replace("www.", "")
        if not host:
            return True
        return any(marker in host for marker in _WB_HOST_MARKERS)
    except Exception:
        return True


def _first_url(value: Any, seed_url: str) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text:
        return ""
    if text.startswith(("http://", "https://", "//", "/")):
        return _abs_url(seed_url, text)
    return ""


def _strip_html(fragment: str) -> str:
    text = _TAG_RE.sub("\n", fragment or "")
    text = html_lib.unescape(text.replace("\xa0", " "))
    return _SPACE_RE.sub(" ", text).strip()


def _looks_blocked(title: str | None, body_text: str | None, html: str | None = None) -> bool:
    blob = " ".join([str(title or ""), str(body_text or ""), str(html or "")[:5000]]).lower()
    return any(marker in blob for marker in _BLOCKED_MARKERS)


def _detect_currency_label(*parts: Any) -> str:
    blob = "\n".join(str(x or "") for x in parts).lower()
    # KZT must win when both values are present in a hidden currency popup. Visible body text is passed first.
    if "₸" in blob or " kzt" in blob or "тенге" in blob or "тг" in blob:
        return "kzt"
    if "₽" in blob or " rub" in blob or "руб" in blob or "российский рубль" in blob:
        return "rub"
    return "unknown"


def _titles_compatible(existing: dict[str, Any], incoming: dict[str, Any]) -> bool:
    """Allow body/HTML enrichment only when title order did not drift."""
    old = _strip_html("\n".join(str(existing.get(k) or "") for k in ("title", "link_text", "aria_label", "image_alt", "container_text")))
    new = _strip_html("\n".join(str(incoming.get(k) or "") for k in ("title", "link_text", "aria_label", "image_alt", "container_text")))
    old_l = old.lower()
    new_l = new.lower()
    if not old_l or not new_l:
        return True
    old_ids = set(re.findall(r"\b(?:dk|aa|bl|kf)[\s\-/]*\d{2,5}\b", old_l, flags=re.IGNORECASE))
    new_ids = set(re.findall(r"\b(?:dk|aa|bl|kf)[\s\-/]*\d{2,5}\b", new_l, flags=re.IGNORECASE))
    if old_ids and new_ids and old_ids.isdisjoint(new_ids):
        return False
    important = (
        "tison", "waison", "duos", "combo", "crispo", "leo", "luneo", "sanders", "tarvin",
        "demixi", "sole", "решет", "решёт", "шампур", "блендер", "суповар", "аэрогр", "печ",
        "корзин", "форма", "пергамент", "чаша",
    )
    old_hits = {x for x in important if x in old_l}
    new_hits = {x for x in important if x in new_l}
    if old_hits and new_hits and old_hits.isdisjoint(new_hits):
        return False
    return True


def _try_force_kzt(page: Any, cfg: dict[str, Any], report: dict[str, Any]) -> None:
    """Try to switch WB desktop page to Kazakhstan/KZT.

    GitHub runners often open WB as San Jose/RUB. That price must never silently become Kaspi KZT.
    This function is a soft UI-level attempt only; if WB keeps RUB, later validation marks records as RUB.
    """
    try:
        text_before = page.locator("body").inner_text(timeout=3000)
    except Exception:
        text_before = ""
    if _detect_currency_label(text_before) == "kzt":
        report["wb_currency_switch"] = "already_kzt"
        return
    try:
        report["wb_currency_switch"] = "attempted"
        selectors = [
            '[data-testid="currency-change-popup"]',
            '[data-testid="selected-currency"]',
            '.header__currency',
        ]
        for selector in selectors:
            try:
                page.locator(selector).first.click(timeout=2500)
                page.wait_for_timeout(800)
                break
            except Exception:
                try:
                    page.locator(selector).first.hover(timeout=1800)
                    page.wait_for_timeout(800)
                    break
                except Exception:
                    pass
        clicked = False
        for selector in ('[data-testid="currency-kz"]', 'label[data-autotest-label="currency-kz"]', 'input[name="currency"][value="KZT"]'):
            try:
                page.locator(selector).first.click(timeout=3500, force=True)
                clicked = True
                break
            except Exception:
                pass
        if not clicked:
            page.evaluate(
                """() => {
                    const el = document.querySelector('[data-testid="currency-kz"], label[data-autotest-label="currency-kz"], input[name="currency"][value="KZT"]');
                    if (!el) return false;
                    el.click();
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                    return true;
                }"""
            )
        page.wait_for_timeout(int(cfg.get("currency_switch_wait_ms") or 5000))
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass
        try:
            text_after = page.locator("body").inner_text(timeout=3000)
        except Exception:
            text_after = ""
        after_currency = _detect_currency_label(text_after)
        report["wb_currency_after_switch"] = after_currency
        if after_currency != "kzt":
            try:
                page.reload(wait_until="domcontentloaded", timeout=int(cfg.get("goto_timeout_ms") or 60000))
                page.wait_for_timeout(int(cfg.get("wait_after_open_ms") or 5000))
            except Exception:
                pass
    except Exception as exc:
        report["wb_currency_switch"] = "failed"
        report["warnings"].append(f"wb_kzt_currency_switch_failed: {exc}")


def _first_image_url(obj: Any, seed_url: str, limit: int = 8000) -> str:
    stack: list[Any] = [obj]
    seen = 0
    while stack and seen < limit:
        seen += 1
        cur = stack.pop()
        if isinstance(cur, dict):
            for key, value in cur.items():
                if isinstance(value, str):
                    url = _first_url(value, seed_url)
                    lower = url.lower()
                    if url and (key in _IMAGE_KEYS or any(ext in lower for ext in (".jpg", ".jpeg", ".png", ".webp"))):
                        return url
                elif isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(cur, list):
            stack.extend(cur[:120])
    return ""


def _wb_price_text(product: dict[str, Any]) -> str:
    for key in ("salePriceU", "priceU", "salePrice", "price", "basicPriceU"):
        value = product.get(key)
        if isinstance(value, (int, float)) and value:
            if key.lower().endswith("u") and value >= 1000:
                value = int(round(float(value) / 100))
            return str(int(value))
    sizes = product.get("sizes")
    if isinstance(sizes, list):
        for size in sizes:
            if not isinstance(size, dict):
                continue
            price = size.get("price") or {}
            if isinstance(price, dict):
                for key in ("total", "product", "basic"):
                    value = price.get(key)
                    if isinstance(value, (int, float)) and value:
                        if value >= 1000:
                            value = int(round(float(value) / 100))
                        return str(int(value))
    return ""


def _wb_stock(product: dict[str, Any]) -> int | None:
    total = product.get("totalQuantity") or product.get("quantity") or product.get("qty")
    if isinstance(total, (int, float)):
        return int(total)
    sizes = product.get("sizes")
    if isinstance(sizes, list):
        qty = 0
        found = False
        for size in sizes:
            if not isinstance(size, dict):
                continue
            stocks = size.get("stocks")
            if isinstance(stocks, list):
                for stock in stocks:
                    if isinstance(stock, dict) and isinstance(stock.get("qty"), (int, float)):
                        qty += int(stock.get("qty") or 0)
                        found = True
        if found:
            return qty
    return None


def _extract_wb_api_products(obj: Any, seed_url: str, limit: int = 3000, expected_brand: str = "") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    stack: list[Any] = [obj]
    seen = 0
    while stack and seen < 60000 and len(out) < limit:
        seen += 1
        cur = stack.pop()
        if isinstance(cur, dict):
            product_id = cur.get("id") or cur.get("nmId") or cur.get("productId")
            name = cur.get("name") or cur.get("title")
            if isinstance(product_id, (int, str)) and isinstance(name, str) and len(name.strip()) >= 4:
                brand = cur.get("brand") or cur.get("brandName") or ""
                price = _wb_price_text(cur)
                title_blob = f"{brand} {name}".lower()
                expected = str(expected_brand or "").lower().strip()
                if not price:
                    stack.extend(cur.values())
                    continue
                if expected and expected not in title_blob:
                    stack.extend(cur.values())
                    continue
                href = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"
                stock = _wb_stock(cur)
                text_lines = [str(brand), str(name), str(price)]
                if stock is not None:
                    text_lines.append(f"Осталось {stock} шт")
                if cur.get("feedbacks") is not None:
                    text_lines.append(f"Отзывы: {cur.get('feedbacks')}")
                out.append(
                    {
                        "href": href,
                        "market_id": str(product_id),
                        "title": f"{brand} / {name}" if brand else str(name),
                        "link_text": str(name),
                        "aria_label": str(name),
                        "brand": str(brand or ""),
                        "price": price,
                        "stock": stock,
                        "available": False if stock == 0 else True,
                        "image": _first_image_url(cur, seed_url),
                        "image_alt": str(name),
                        "container_text": "\n".join(x for x in text_lines if x),
                        "html": "",
                        "extract_method": "network_json_wb_api",
                    }
                )
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur[:300])
    return out


def _json_objects_from_text(text: str, limit: int = 30) -> list[Any]:
    out: list[Any] = []
    stripped = text.strip()
    if not stripped:
        return out
    if stripped[:1] in "[{":
        try:
            out.append(json.loads(stripped))
            return out
        except Exception:
            pass
    patterns = [
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(?P<json>.*?)</script>',
        r'window\.__INITIAL_STATE__\s*=\s*(?P<json>\{.*?\})\s*;',
        r'window\.__NUXT__\s*=\s*(?P<json>\{.*?\})\s*;',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            if len(out) >= limit:
                return out
            blob = match.group("json")
            try:
                out.append(json.loads(blob))
            except Exception:
                continue
    return out


def _snippet_around(html: str, start: int, end: int) -> str:
    left_candidates = [
        html.rfind('<article', 0, start),
        html.rfind('<div class="product-card', 0, start),
        html.rfind("<div class='product-card", 0, start),
        html.rfind('<div class="product-card__wrapper', 0, start),
    ]
    left = max(left_candidates)
    if left < 0 or start - left > 7000:
        left = max(0, start - 1800)
    right_markers = [
        html.find('<article', end),
        html.find('<div class="product-card', end),
        html.find("<div class='product-card", end),
    ]
    right_markers = [x for x in right_markers if x > end]
    right = min(right_markers) if right_markers else min(len(html), end + 2200)
    return html[left:right]


def _cards_from_html_regex(html: str, seed_url: str, limit: int = 3000, expected_brand: str = "") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for regex in (_HREF_RE, _ANY_URL_RE):
        for match in regex.finditer(html or ""):
            if len(out) >= limit:
                break
            href = _clean_url(_abs_url(seed_url, match.group("href")))
            if href in seen or not _is_wb_product_url(href) or not _same_wb_family(href):
                continue
            fragment = _snippet_around(html, match.start(), match.end())
            text = _strip_html(fragment)
            low = text.lower()
            brand_l = str(expected_brand or "").lower().strip()
            if brand_l and brand_l not in low and "demiand" not in low:
                continue
            if not any(hint in low for hint in _WB_TYPE_HINTS) and "demiand" not in low:
                continue
            seen.add(href)
            out.append(
                {
                    "href": href,
                    "link_text": "",
                    "aria_label": "",
                    "brand": expected_brand if (expected_brand and expected_brand.lower() in low) else "",
                    "image": "",
                    "image_alt": "",
                    "container_text": text,
                    "html": fragment[:5000],
                    "extract_method": "html_regex_wb",
                }
            )
        if len(out) >= limit:
            break
    return out


def _extract_script() -> str:
    return r"""
    ({brand}) => {
      const brandText = String(brand || '').trim().toLowerCase();
      const isBrandCard = (text) => {
        if (!brandText) return true;
        const low = String(text || '').toLowerCase();
        return low.includes(brandText) || low.includes('demiand') || low.includes('демианд');
      };
      const pickContainer = (a) => {
        const preferred = a.closest('[class*=product-card], [class*=goods-tile], [data-nm-id], article, li');
        if (preferred) return preferred;
        let node = a;
        let best = a;
        for (let i = 0; i < 10 && node; i += 1) {
          const text = (node.innerText || '').trim();
          if (text.length > ((best.innerText || '').trim().length || 0) && text.length < 2500) best = node;
          node = node.parentElement;
        }
        return best;
      };
      const out = [];
      const seen = new Set();
      const anchors = Array.from(document.querySelectorAll('a[href]'));
      for (const a of anchors) {
        const href = a.href || a.getAttribute('href') || '';
        const lower = href.toLowerCase();
        const ok = lower.includes('/catalog/') && lower.includes('/detail');
        if (!ok || seen.has(href)) continue;
        const box = pickContainer(a);
        const img = box ? box.querySelector('img') : null;
        const imgSrc = img ? (img.currentSrc || img.src || img.getAttribute('src') || '') : '';
        const imgAlt = img ? (img.alt || img.getAttribute('alt') || '') : '';
        const aria = a.getAttribute('aria-label') || a.getAttribute('title') || '';
        const containerText = box ? (box.innerText || '').trim() : '';
        const allText = [containerText, aria, imgAlt, a.innerText || ''].join('\n');
        if (!isBrandCard(allText)) continue;
        seen.add(href);
        out.push({
          href,
          link_text: (a.innerText || '').trim(),
          aria_label: aria.trim(),
          brand: brandText ? brandText.toUpperCase() : '',
          image: imgSrc,
          image_alt: imgAlt.trim(),
          container_text: containerText,
          html: box ? box.outerHTML.slice(0, 5000) : '',
          extract_method: 'dom_anchor_wb'
        });
      }
      return out;
    }
    """.strip()


def _product_urls_from_html(html: str, seed_url: str, limit: int = 3000) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for regex in (_HREF_RE, _ANY_URL_RE):
        for match in regex.finditer(html or ""):
            href = _clean_url(_abs_url(seed_url, match.group("href")))
            if href in seen or not _is_wb_product_url(href) or not _same_wb_family(href):
                continue
            seen.add(href)
            urls.append(href)
            if len(urls) >= limit:
                return urls
    return urls


def _cards_from_wb_body_text(text: str, html: str, seed: dict[str, Any], seed_url: str, limit: int = 3000) -> list[dict[str, Any]]:
    brand = str(seed.get("brand") or "").strip()
    brand_l = brand.lower()
    lines = [_SPACE_RE.sub(" ", html_lib.unescape(line).replace("\xa0", " ")).strip() for line in (text or "").splitlines()]
    lines = [line for line in lines if line]
    urls = _product_urls_from_html(html, seed_url, limit=limit)
    out: list[dict[str, Any]] = []
    title_indexes: list[int] = []
    for idx, line in enumerate(lines):
        low = line.lower()
        if brand_l and brand_l not in low and "demiand" not in low:
            continue
        if not any(x in low for x in _WB_TYPE_HINTS):
            continue
        title_indexes.append(idx)
    for card_idx, idx in enumerate(title_indexes[:limit]):
        start = max(0, idx - 10)
        end = min(len(lines), idx + 10)
        block_lines = lines[start:end]
        href = urls[card_idx] if card_idx < len(urls) else ""
        if not href:
            continue
        title = lines[idx]
        out.append(
            {
                "href": href,
                "title": title,
                "link_text": title,
                "aria_label": title,
                "brand": brand,
                "image": "",
                "image_alt": title,
                "container_text": "\n".join(block_lines),
                "price_currency": _detect_currency_label("\n".join(block_lines)).upper() if _detect_currency_label("\n".join(block_lines)) in ("kzt", "rub") else None,
                "html": "",
                "extract_method": "body_text_wb_listing",
            }
        )
    return out


def _merge_card(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    existing_text = str(existing.get("container_text") or "")
    incoming_text = str(incoming.get("container_text") or "")
    for key in ("market_id", "brand", "price", "old_price", "stock", "available", "image", "image_alt", "link_text", "aria_label", "eta_text", "price_currency"):
        if existing.get(key) in (None, "", 0) and incoming.get(key) not in (None, ""):
            existing[key] = incoming.get(key)
    if incoming_text and incoming_text not in existing_text:
        existing["container_text"] = (existing_text + "\n" + incoming_text).strip()
    methods = [x for x in str(existing.get("extract_method") or "").split("+") if x]
    method = str(incoming.get("extract_method") or "")
    if method and method not in methods:
        methods.append(method)
        existing["extract_method"] = "+".join(methods)


def _add_raw_cards(
    cards_by_url: dict[str, dict[str, Any]],
    raw_cards: list[dict[str, Any]],
    seed: dict[str, Any],
    seed_url: str,
    max_cards: int,
) -> int:
    added = 0
    for raw in raw_cards or []:
        href = _clean_url(_abs_url(seed_url, str(raw.get("href") or "")))
        if not href or not _is_wb_product_url(href) or not _same_wb_family(href):
            continue
        raw.update({"href": href, "seed_key": seed.get("seed_key"), "source": "wb", "seed_url": seed_url})
        if href not in cards_by_url:
            cards_by_url[href] = raw
            added += 1
        else:
            if _titles_compatible(cards_by_url[href], raw):
                _merge_card(cards_by_url[href], raw)
            elif len(str(raw.get("container_text") or "")) > len(str(cards_by_url[href].get("container_text") or "")):
                raw["merge_warning"] = "same_url_title_mismatch_replaced_by_richer_card"
                cards_by_url[href] = raw
        if len(cards_by_url) >= max_cards:
            break
    return added


def _safe_response_text(response: Any, max_chars: int = 2_000_000) -> str:
    try:
        body = response.text()
        if isinstance(body, str):
            return body[:max_chars]
    except Exception:
        return ""
    return ""


def fetch_seed(seed: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = str(seed.get("source") or "").strip().lower()
    seed_key = seed.get("seed_key") or "wb_seed"
    url = str(seed.get("url") or "").strip()
    cfg = browser_cfg()
    max_cards = int(discovery_cfg().get("max_cards_per_seed") or 1200)
    max_rounds = int(cfg.get("max_scroll_rounds") or 40)
    no_new_limit = int(cfg.get("stop_after_rounds_without_new") or 5)

    report: dict[str, Any] = {
        "seed_key": seed_key,
        "source": source,
        "url": url,
        "status": "started",
        "errors": [],
        "warnings": [],
        "cards_from_dom": 0,
        "cards_from_network": 0,
        "cards_from_html": 0,
        "network_json_seen": 0,
    }
    cards_by_url: dict[str, dict[str, Any]] = {}
    network_urls: list[str] = []
    dom_cards_total = 0
    network_cards_total = 0
    html_cards_total = 0
    network_json_seen = 0
    no_new = 0
    blocked_detected = False
    last_body_text = ""
    last_page_html = ""

    if not url or source != "wb":
        report["status"] = "skipped"
        report["errors"].append("Only WB seeds are supported in CS-Kaspi v7 WB-only.")
        return [], report

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=bool(cfg.get("headless", True)),
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = browser.new_context(
                viewport={"width": int(cfg.get("viewport_width") or 1440), "height": int(cfg.get("viewport_height") or 1400)},
                locale="ru-KZ",
                timezone_id="Asia/Almaty",
                geolocation={"latitude": 43.238949, "longitude": 76.889709},
                permissions=["geolocation"],
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                extra_http_headers={"Accept-Language": "ru-KZ,ru;q=0.9,en-US;q=0.7,en;q=0.6"},
            )
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            page = context.new_page()

            def on_response(response: Any) -> None:
                nonlocal network_cards_total, network_json_seen
                if len(cards_by_url) >= max_cards:
                    return
                response_url = str(getattr(response, "url", "") or "")
                response_url_l = response_url.lower()
                if not any(x in response_url_l for x in ("wildberries", "wb.ru", "wbbasket", "catalog.wb")):
                    return
                if len(network_urls) < 80:
                    network_urls.append(response_url)
                try:
                    headers = getattr(response, "headers", {}) or {}
                    content_type = str(headers.get("content-type") or headers.get("Content-Type") or "").lower()
                    interesting_url = any(x in response_url_l for x in ("catalog", "search", "card", "product", "searchresult"))
                    if "json" not in content_type and not interesting_url:
                        return
                    text = _safe_response_text(response)
                    if not text:
                        return
                    json_objects = _json_objects_from_text(text)
                    if not json_objects:
                        return
                    network_json_seen += len(json_objects)
                    raw_cards: list[dict[str, Any]] = []
                    for data in json_objects:
                        raw_cards.extend(_extract_wb_api_products(data, url, max_cards, str(seed.get("brand") or "")))
                    network_cards_total += _add_raw_cards(cards_by_url, raw_cards, seed, url, max_cards)
                except Exception as exc:
                    if len(report["warnings"]) < 20:
                        report["warnings"].append(f"network_parse_warning: {exc}")

            page.on("response", on_response)
            page.goto(url, wait_until="domcontentloaded", timeout=int(cfg.get("goto_timeout_ms") or 60000))
            page.wait_for_timeout(int(cfg.get("wait_after_open_ms") or 5000))
            try:
                page.wait_for_load_state("networkidle", timeout=18000)
            except Exception:
                pass
            report["final_url"] = page.url
            try:
                report["page_title"] = page.title()
            except Exception:
                pass

            _try_force_kzt(page, cfg, report)

            try:
                first_html = page.content()
                try:
                    first_text = page.locator("body").inner_text(timeout=3000)
                except Exception:
                    first_text = _strip_html(first_html)
                if _looks_blocked(report.get("page_title"), first_text, first_html):
                    blocked_detected = True
                    report["warnings"].append("wb_blocked_or_antibot_page_detected")
                    # One soft reload/wait is allowed for slow WB pages. No aggressive bypass.
                    try:
                        page.wait_for_timeout(int(cfg.get("blocked_soft_wait_ms") or 9000))
                        page.reload(wait_until="domcontentloaded", timeout=int(cfg.get("goto_timeout_ms") or 60000))
                        page.wait_for_timeout(int(cfg.get("wait_after_open_ms") or 5000))
                        report["page_title_after_soft_reload"] = page.title()
                    except Exception as exc:
                        report["warnings"].append(f"blocked_soft_reload_failed: {exc}")
            except Exception:
                pass

            for round_idx in range(max_rounds + 1):
                before = len(cards_by_url)
                try:
                    raw_cards = page.evaluate(_extract_script(), {"brand": str(seed.get("brand") or "")})
                    dom_cards_total += _add_raw_cards(cards_by_url, raw_cards or [], seed, url, max_cards)
                except Exception as exc:
                    msg = str(exc)
                    if "Execution context was destroyed" in msg or "navigation" in msg.lower():
                        if "page_reloaded_during_scroll" not in report["warnings"]:
                            report["warnings"].append("page_reloaded_during_scroll")
                        try:
                            page.wait_for_load_state("domcontentloaded", timeout=10000)
                        except Exception:
                            pass
                    elif len(report["warnings"]) < 20:
                        report["warnings"].append(f"dom_extract_warning: {msg}")

                try:
                    page_html = page.content()
                    if round_idx in {0, max_rounds} or len(cards_by_url) == 0:
                        html_cards_total += _add_raw_cards(cards_by_url, _cards_from_html_regex(page_html, url, max_cards, str(seed.get("brand") or "")), seed, url, max_cards)
                        for data in _json_objects_from_text(page_html, limit=10):
                            html_cards_total += _add_raw_cards(
                                cards_by_url,
                                _extract_wb_api_products(data, url, max_cards, str(seed.get("brand") or "")),
                                seed,
                                url,
                                max_cards,
                            )
                except Exception:
                    pass

                report["scroll_rounds"] = round_idx
                if len(cards_by_url) == before:
                    no_new += 1
                else:
                    no_new = 0
                if len(cards_by_url) >= max_cards or no_new >= no_new_limit:
                    break

                step = int(cfg.get("scroll_step_px") or 1200)
                try:
                    page.evaluate("(step) => window.scrollBy(0, Math.max(window.innerHeight, step))", step)
                except Exception:
                    try:
                        page.mouse.wheel(0, step)
                    except Exception:
                        pass
                page.wait_for_timeout(int(cfg.get("scroll_wait_ms") or 1500))

            try:
                final_html = page.content()
                try:
                    text = page.locator("body").inner_text(timeout=5000)
                except Exception:
                    text = _strip_html(final_html)
                last_body_text = text or ""
                last_page_html = final_html or ""
                report["body_text_length"] = len(text or "")
                blocked_detected = blocked_detected or _looks_blocked(report.get("page_title"), text, final_html)
                # Body text contains visible WB price currency and delivery date. Use it only as guarded enrichment.
                body_cards = _cards_from_wb_body_text(text or "", final_html or "", seed, url, max_cards)
                html_cards_total += _add_raw_cards(cards_by_url, body_cards, seed, url, max_cards)
                html_cards_total += _add_raw_cards(cards_by_url, _cards_from_html_regex(final_html, url, max_cards, str(seed.get("brand") or "")), seed, url, max_cards)
                _write_debug(seed_key, "page.html", final_html[:1_500_000])
                _write_debug(seed_key, "body.txt", (text or "")[:120_000])
                _write_debug(seed_key, "network_urls.txt", "\n".join(network_urls))
                try:
                    page.screenshot(path=str((_debug_dir() or Path(".")) / f"{_slug(seed_key)}__screenshot.png"), full_page=True, timeout=15000)
                except Exception:
                    pass
            except Exception:
                pass

            try:
                browser.close()
            except Exception:
                pass
    except Exception as exc:
        report["status"] = "failed" if not cards_by_url else "partial"
        report["errors"].append(str(exc))
        report["cards_from_dom"] = dom_cards_total
        report["cards_from_network"] = network_cards_total
        report["cards_from_html"] = html_cards_total
        report["network_json_seen"] = network_json_seen
        report["network_urls_sample"] = network_urls[:25]
        report["cards_seen_raw"] = len(cards_by_url)
        report["cards_unique_url"] = len(cards_by_url)
        return list(cards_by_url.values()), report

    report["cards_from_dom"] = dom_cards_total
    report["cards_from_network"] = network_cards_total
    report["cards_from_html"] = html_cards_total
    report["network_json_seen"] = network_json_seen
    report["network_urls_sample"] = network_urls[:25]
    report["cards_seen_raw"] = len(cards_by_url)
    report["cards_unique_url"] = len(cards_by_url)
    expected_min = int(seed.get("expected_min_cards") or 0)
    page_currency = "unknown"
    try:
        card_text = "\n".join(str(card.get("container_text") or "") for card in cards_by_url.values())
        page_currency = _detect_currency_label(last_body_text, card_text, last_page_html[:3000])
    except Exception:
        page_currency = "unknown"
    report["price_currency_detected"] = page_currency
    if page_currency in ("rub", "kzt"):
        for card in cards_by_url.values():
            if card.get("price") not in (None, "", 0) and not card.get("price_currency"):
                card["price_currency"] = page_currency.upper()
    if page_currency == "rub":
        report["warnings"].append("wb_price_currency_rub_detected_expected_kzt")
    if expected_min and len(cards_by_url) < expected_min:
        report["warnings"].append(f"cards_below_expected_min: expected_min={expected_min}, found={len(cards_by_url)}")
    if blocked_detected:
        report["warnings"].append("blocked_page_needs_manual_check_or_retry")
    if not cards_by_url and report.get("body_text_length", 0) < 1000:
        report["warnings"].append("page_body_too_small_or_blocked")
    if cards_by_url and page_currency == "rub":
        report["status"] = "wrong_currency"
    elif cards_by_url:
        report["status"] = "ok"
    elif blocked_detected:
        report["status"] = "blocked"
    else:
        report["status"] = "empty"
    return list(cards_by_url.values()), report
