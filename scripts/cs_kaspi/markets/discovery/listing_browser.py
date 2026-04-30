from __future__ import annotations

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
_URL_KEYS = ("href", "url", "link", "action", "deeplink", "shareUrl", "productUrl", "cardUrl", "urlModel")
_IMAGE_KEYS = ("image", "imageUrl", "img", "src", "cover", "picture", "thumbnail", "preview")
_WB_TYPE_HINTS = ("аэрогр", "кофевар", "блендер", "печ", "шампур", "аксессуар", "форма", "решет", "корзин")


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
    href = (href or "").strip()
    if href.startswith("//"):
        scheme = urlparse(seed_url).scheme or "https"
        return f"{scheme}:{href}"
    return urljoin(seed_url, href)


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


def _compact_json_text(obj: Any, limit: int = 2400) -> str:
    parts: list[str] = []
    stack: list[Any] = [obj]
    seen = 0
    while stack and seen < 8000 and len("\n".join(parts)) < limit:
        seen += 1
        cur = stack.pop()
        if isinstance(cur, dict):
            for key, value in cur.items():
                if isinstance(value, str) and (key in _TEXT_KEYS or len(value) >= 8):
                    clean = re.sub(r"\s+", " ", value).strip()
                    if clean and clean not in parts:
                        parts.append(clean)
                elif isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(cur, list):
            stack.extend(cur[:120])
        elif isinstance(cur, str):
            clean = re.sub(r"\s+", " ", cur).strip()
            if len(clean) >= 8 and clean not in parts:
                parts.append(clean)
    return "\n".join(parts)[:limit]


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


def _cards_from_html_regex(html: str, seed_url: str, limit: int = 3000) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    pattern = r'(?:href=|url["\']?\s*[:=]\s*)["\'](?P<href>[^"\']*/catalog/\d+/detail[^"\']*)["\']'
    for match in re.finditer(pattern, html or "", flags=re.IGNORECASE):
        if len(out) >= limit:
            break
        href = _abs_url(seed_url, match.group("href"))
        if href in seen or not _same_wb_family(href):
            continue
        seen.add(href)
        start = max(0, match.start() - 1300)
        end = min(len(html), match.end() + 1300)
        snippet = re.sub(r"<[^>]+>", " ", html[start:end])
        snippet = re.sub(r"\s+", " ", snippet).strip()
        out.append(
            {
                "href": href,
                "link_text": "",
                "aria_label": "",
                "image": "",
                "image_alt": "",
                "container_text": snippet,
                "html": html[start:end][:3000],
                "extract_method": "html_regex_wb",
            }
        )
    return out


def _extract_script() -> str:
    return r"""
    ({brand}) => {
      const brandText = String(brand || '').trim().toLowerCase();
      const isBrandCard = (text) => {
        if (!brandText) return true;
        return String(text || '').toLowerCase().includes(brandText);
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
          image: imgSrc,
          image_alt: imgAlt.trim(),
          container_text: containerText,
          html: box ? box.outerHTML.slice(0, 3000) : '',
          extract_method: 'dom_anchor_wb'
        });
      }
      return out;
    }
    """.strip()


def _product_urls_from_html(html: str, seed_url: str, limit: int = 3000) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    pattern = r'(?:href=|url["\']?\s*[:=]\s*)["\'](?P<href>[^"\']*/catalog/\d+/detail[^"\']*)["\']'
    for match in re.finditer(pattern, html or "", flags=re.IGNORECASE):
        href = _abs_url(seed_url, match.group("href"))
        if href in seen or not _same_wb_family(href):
            continue
        seen.add(href)
        urls.append(href)
        if len(urls) >= limit:
            break
    return urls


def _cards_from_wb_body_text(text: str, html: str, seed: dict[str, Any], seed_url: str, limit: int = 3000) -> list[dict[str, Any]]:
    brand = str(seed.get("brand") or "").strip()
    brand_l = brand.lower()
    lines = [re.sub(r"\s+", " ", line).strip() for line in (text or "").splitlines()]
    lines = [line for line in lines if line]
    urls = _product_urls_from_html(html, seed_url, limit=limit)
    out: list[dict[str, Any]] = []
    title_indexes: list[int] = []
    for idx, line in enumerate(lines):
        low = line.lower()
        if brand_l and brand_l not in low:
            continue
        if not any(x in low for x in _WB_TYPE_HINTS):
            continue
        title_indexes.append(idx)
    for card_idx, idx in enumerate(title_indexes[:limit]):
        start = max(0, idx - 10)
        end = min(len(lines), idx + 8)
        block_lines = lines[start:end]
        href = urls[card_idx] if card_idx < len(urls) else ""
        if not href:
            continue
        title = lines[idx]
        out.append(
            {
                "href": href,
                "link_text": title,
                "aria_label": title,
                "image": "",
                "image_alt": title,
                "container_text": "\n".join(block_lines),
                "html": "",
                "extract_method": "body_text_wb_listing",
            }
        )
    return out


def _add_raw_cards(
    cards_by_url: dict[str, dict[str, Any]],
    raw_cards: list[dict[str, Any]],
    seed: dict[str, Any],
    seed_url: str,
    max_cards: int,
) -> int:
    added = 0
    for raw in raw_cards or []:
        href = _abs_url(seed_url, str(raw.get("href") or ""))
        if not href or not _is_wb_product_url(href) or not _same_wb_family(href):
            continue
        if href not in cards_by_url:
            raw.update({"href": href, "seed_key": seed.get("seed_key"), "source": "wb", "seed_url": seed_url})
            cards_by_url[href] = raw
            added += 1
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
                locale="ru-RU",
                timezone_id="Asia/Almaty",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                extra_http_headers={"Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"},
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
                    html = page.content()
                    if round_idx in {0, max_rounds} or len(cards_by_url) == 0:
                        html_cards_total += _add_raw_cards(cards_by_url, _cards_from_html_regex(html, url, max_cards), seed, url, max_cards)
                        for data in _json_objects_from_text(html, limit=10):
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
                html = page.content()
                try:
                    text = page.locator("body").inner_text(timeout=5000)
                except Exception:
                    text = re.sub(r"<[^>]+>", " ", html)
                report["body_text_length"] = len(text or "")
                body_cards = _cards_from_wb_body_text(text or "", html or "", seed, url, max_cards)
                html_cards_total += _add_raw_cards(cards_by_url, body_cards, seed, url, max_cards)
                _write_debug(seed_key, "page.html", html[:1_500_000])
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
    if expected_min and len(cards_by_url) < expected_min:
        report["warnings"].append(f"cards_below_expected_min: expected_min={expected_min}, found={len(cards_by_url)}")
    if not cards_by_url and report.get("body_text_length", 0) < 1000:
        report["warnings"].append("page_body_too_small_or_blocked")
    report["status"] = "ok" if cards_by_url else "empty"
    return list(cards_by_url.values()), report
