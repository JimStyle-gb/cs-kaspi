from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from .seed_config import browser_cfg, discovery_cfg

_PRODUCT_URL_MARKERS = {
    "ozon": ("/product/",),
    "wb": ("/catalog/", "/detail"),
}

_MARKET_HOST_MARKERS = {
    "ozon": ("ozon.",),
    "wb": ("wildberries.", "wb.ru"),
}

_TEXT_KEYS = (
    "title", "name", "text", "label", "caption", "subtitle", "brand", "seller", "delivery", "price", "finalPrice",
    "cardPrice", "salePrice", "marketingLabel", "description",
)

_URL_KEYS = ("href", "url", "link", "action", "deeplink", "shareUrl", "productUrl", "cardUrl")
_IMAGE_KEYS = ("image", "imageUrl", "img", "src", "cover", "picture", "thumbnail")


def _abs_url(seed_url: str, href: str) -> str:
    href = (href or "").strip()
    if href.startswith("//"):
        scheme = urlparse(seed_url).scheme or "https"
        return f"{scheme}:{href}"
    return urljoin(seed_url, href)


def _is_product_url(source: str, href: str) -> bool:
    href_l = (href or "").lower()
    markers = _PRODUCT_URL_MARKERS.get(source, ())
    if source == "wb":
        return all(m in href_l for m in markers)
    return any(m in href_l for m in markers)


def _same_market_family(source: str, href: str) -> bool:
    try:
        host = urlparse(href).netloc.lower().replace("www.", "")
        if not host:
            return True
        return any(marker in host for marker in _MARKET_HOST_MARKERS.get(source, ()))
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


def _first_image_url(obj: Any, seed_url: str, limit: int = 6000) -> str:
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
            stack.extend(cur[:80])
    return ""


def _compact_json_text(obj: Any, limit: int = 2200) -> str:
    parts: list[str] = []
    stack: list[Any] = [obj]
    seen = 0
    while stack and seen < 5000 and len("\n".join(parts)) < limit:
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
            stack.extend(cur[:80])
        elif isinstance(cur, str):
            clean = re.sub(r"\s+", " ", cur).strip()
            if len(clean) >= 8 and clean not in parts:
                parts.append(clean)
    return "\n".join(parts)[:limit]


def _extract_product_links_from_json(source: str, obj: Any, seed_url: str, limit: int = 2500) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    stack: list[Any] = [obj]
    seen = 0
    while stack and seen < 35000 and len(out) < limit:
        seen += 1
        cur = stack.pop()
        if isinstance(cur, dict):
            href = ""
            for key in _URL_KEYS:
                value = cur.get(key)
                if isinstance(value, str):
                    candidate = _first_url(value, seed_url)
                    if candidate and _is_product_url(source, candidate):
                        href = candidate
                        break
            if href and _same_market_family(source, href):
                text = _compact_json_text(cur)
                out.append(
                    {
                        "href": href,
                        "link_text": "",
                        "aria_label": "",
                        "image": _first_image_url(cur, seed_url),
                        "image_alt": "",
                        "container_text": text,
                        "html": "",
                        "extract_method": "network_json_generic",
                    }
                )
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur[:250])
    return out


def _wb_price_text(product: dict[str, Any]) -> str:
    for key in ("salePriceU", "priceU", "salePrice", "price", "basicPriceU", "logisticsCost"):
        value = product.get(key)
        if isinstance(value, (int, float)) and value:
            # WB API often returns prices in minor units.
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


def _extract_wb_api_products(obj: Any, seed_url: str, limit: int = 2500) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    stack: list[Any] = [obj]
    seen = 0
    while stack and seen < 35000 and len(out) < limit:
        seen += 1
        cur = stack.pop()
        if isinstance(cur, dict):
            product_id = cur.get("id") or cur.get("nmId") or cur.get("productId")
            name = cur.get("name") or cur.get("title")
            if isinstance(product_id, (int, str)) and isinstance(name, str) and len(name.strip()) >= 4:
                href = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"
                brand = cur.get("brand") or cur.get("brandName") or ""
                price = _wb_price_text(cur)
                text_lines = [str(brand), name]
                if price:
                    text_lines.append(price)
                if cur.get("feedbacks") is not None:
                    text_lines.append(f"Отзывы: {cur.get('feedbacks')}")
                out.append(
                    {
                        "href": href,
                        "link_text": name,
                        "aria_label": name,
                        "image": _first_image_url(cur, seed_url),
                        "image_alt": name,
                        "container_text": "\n".join(x for x in text_lines if x),
                        "html": "",
                        "extract_method": "network_json_wb_api",
                    }
                )
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur[:250])
    return out


def _extract_script() -> str:
    return r"""
    ({source}) => {
      const pickContainer = (a) => {
        let node = a;
        let best = a;
        for (let i = 0; i < 8 && node; i += 1) {
          const text = (node.innerText || '').trim();
          if (text.length > ((best.innerText || '').trim().length || 0)) best = node;
          node = node.parentElement;
        }
        return best;
      };
      const out = [];
      const anchors = Array.from(document.querySelectorAll('a[href]'));
      for (const a of anchors) {
        const href = a.href || a.getAttribute('href') || '';
        const lower = href.toLowerCase();
        let ok = false;
        if (source === 'ozon') ok = lower.includes('/product/');
        if (source === 'wb') ok = lower.includes('/catalog/') && lower.includes('/detail');
        if (!ok) continue;
        const box = pickContainer(a);
        const img = box ? box.querySelector('img') : null;
        const imgSrc = img ? (img.currentSrc || img.src || img.getAttribute('src') || '') : '';
        const imgAlt = img ? (img.alt || img.getAttribute('alt') || '') : '';
        const aria = a.getAttribute('aria-label') || a.getAttribute('title') || '';
        out.push({
          href,
          link_text: (a.innerText || '').trim(),
          aria_label: aria.trim(),
          image: imgSrc,
          image_alt: imgAlt.trim(),
          container_text: box ? (box.innerText || '').trim() : '',
          html: box ? box.outerHTML.slice(0, 3000) : '',
          extract_method: 'dom_anchor'
        });
      }
      return out;
    }
    """.strip()


def _add_raw_cards(
    cards_by_url: dict[str, dict[str, Any]],
    raw_cards: list[dict[str, Any]],
    seed: dict[str, Any],
    source: str,
    seed_url: str,
    max_cards: int,
) -> int:
    added = 0
    for raw in raw_cards or []:
        href = _abs_url(seed_url, str(raw.get("href") or ""))
        if not href or not _is_product_url(source, href) or not _same_market_family(source, href):
            continue
        if href not in cards_by_url:
            raw.update({"href": href, "seed_key": seed.get("seed_key"), "source": source, "seed_url": seed_url})
            cards_by_url[href] = raw
            added += 1
        if len(cards_by_url) >= max_cards:
            break
    return added


def fetch_seed(seed: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cfg = browser_cfg()
    disc = discovery_cfg()
    source = str(seed.get("source") or "").lower().strip()
    url = str(seed.get("url") or "").strip()
    report: dict[str, Any] = {
        "seed_key": seed.get("seed_key"),
        "source": source,
        "url": url,
        "status": "started",
        "scroll_rounds": 0,
        "cards_seen_raw": 0,
        "cards_unique_url": 0,
        "cards_from_dom": 0,
        "cards_from_network": 0,
        "final_url": "",
        "warnings": [],
        "errors": [],
    }
    if not url or source not in {"ozon", "wb"}:
        report["status"] = "failed"
        report["errors"].append("bad_seed_config")
        return [], report

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - depends on CI env
        report["status"] = "failed"
        report["errors"].append(f"playwright_not_available: {exc}")
        return [], report

    cards_by_url: dict[str, dict[str, Any]] = {}
    max_cards = int(disc.get("max_cards_per_seed") or 1200)
    no_new_limit = int(cfg.get("stop_after_rounds_without_new") or 5)
    max_rounds = int(cfg.get("max_scroll_rounds") or 55)
    no_new = 0
    network_cards_total = 0
    dom_cards_total = 0

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=bool(cfg.get("headless", True)))
            context = browser.new_context(
                viewport={"width": int(cfg.get("viewport_width") or 1440), "height": int(cfg.get("viewport_height") or 1400)},
                locale="ru-RU",
                timezone_id="Asia/Almaty",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            def on_response(response: Any) -> None:
                nonlocal network_cards_total
                if len(cards_by_url) >= max_cards:
                    return
                response_url = str(getattr(response, "url", "") or "").lower()
                if source == "ozon" and "ozon" not in response_url:
                    return
                if source == "wb" and not ("wildberries" in response_url or "wb.ru" in response_url):
                    return
                try:
                    headers = getattr(response, "headers", {}) or {}
                    content_type = str(headers.get("content-type") or headers.get("Content-Type") or "").lower()
                    if "json" not in content_type and not any(x in response_url for x in ("catalog", "search", "card", "product", "widget")):
                        return
                    data = response.json()
                except Exception:
                    return
                try:
                    raw_cards: list[dict[str, Any]] = []
                    if source == "wb":
                        raw_cards.extend(_extract_wb_api_products(data, url, max_cards))
                    raw_cards.extend(_extract_product_links_from_json(source, data, url, max_cards))
                    added = _add_raw_cards(cards_by_url, raw_cards, seed, source, url, max_cards)
                    network_cards_total += added
                except Exception as exc:
                    report["warnings"].append(f"network_parse_warning: {exc}")

            page.on("response", on_response)
            page.goto(url, wait_until="domcontentloaded", timeout=int(cfg.get("goto_timeout_ms") or 60000))
            page.wait_for_timeout(int(cfg.get("wait_after_open_ms") or 3000))
            try:
                page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            report["final_url"] = page.url

            for round_idx in range(max_rounds + 1):
                before = len(cards_by_url)
                try:
                    raw_cards = page.evaluate(_extract_script(), {"source": source})
                    dom_cards_total += _add_raw_cards(cards_by_url, raw_cards or [], seed, source, url, max_cards)
                except Exception as exc:
                    msg = str(exc)
                    if "Execution context was destroyed" in msg or "navigation" in msg.lower():
                        report["warnings"].append("page_reloaded_during_scroll")
                        try:
                            page.wait_for_load_state("domcontentloaded", timeout=10000)
                        except Exception:
                            pass
                    else:
                        report["warnings"].append(f"dom_extract_warning: {msg}")

                report["scroll_rounds"] = round_idx
                if len(cards_by_url) == before:
                    no_new += 1
                else:
                    no_new = 0
                if len(cards_by_url) >= max_cards or no_new >= no_new_limit:
                    break

                try:
                    page.evaluate("window.scrollBy(0, Math.max(window.innerHeight, arguments[0]));", int(cfg.get("scroll_step_px") or 1200))
                except Exception:
                    try:
                        page.mouse.wheel(0, int(cfg.get("scroll_step_px") or 1200))
                    except Exception:
                        pass
                page.wait_for_timeout(int(cfg.get("scroll_wait_ms") or 1200))

            try:
                browser.close()
            except Exception:
                pass
    except Exception as exc:
        report["status"] = "failed" if not cards_by_url else "partial"
        report["errors"].append(str(exc))
        report["cards_from_dom"] = dom_cards_total
        report["cards_from_network"] = network_cards_total
        report["cards_seen_raw"] = len(cards_by_url)
        report["cards_unique_url"] = len(cards_by_url)
        return list(cards_by_url.values()), report

    report["cards_from_dom"] = dom_cards_total
    report["cards_from_network"] = network_cards_total
    report["cards_seen_raw"] = len(cards_by_url)
    report["cards_unique_url"] = len(cards_by_url)
    expected_min = int(seed.get("expected_min_cards") or 0)
    if expected_min and len(cards_by_url) < expected_min:
        report["warnings"].append(f"cards_below_expected_min: expected_min={expected_min}, found={len(cards_by_url)}")
    report["status"] = "ok" if cards_by_url else "empty"
    return list(cards_by_url.values()), report
