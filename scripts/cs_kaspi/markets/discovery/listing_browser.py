from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote, urljoin, urlparse

from .seed_config import browser_cfg, discovery_cfg

_PRODUCT_URL_MARKERS = {
    "ozon": ("/product/",),
    "wb": ("/catalog/", "/detail"),
}

_OZON_ENTRYPOINT_MARKER = "/api/entrypoint-api.bx/page/json/v2"
_OZON_TILE_WIDGET_HINTS = ("tileGridDesktop", "catalog.searchResultsV2", "searchResultsV2")


def _is_product_url(source: str, href: str) -> bool:
    href_l = (href or "").lower()
    markers = _PRODUCT_URL_MARKERS.get(source, ())
    if source == "wb":
        return all(m in href_l for m in markers)
    return any(m in href_l for m in markers)


def _same_domain(url: str, href: str) -> bool:
    try:
        base_host = urlparse(url).netloc.replace("www.", "")
        href_host = urlparse(href).netloc.replace("www.", "")
        if not href_host:
            return True
        if "ozon" in base_host and "ozon" in href_host:
            return True
        if ("wildberries" in base_host or base_host.startswith("wb.")) and (
            "wildberries" in href_host or href_host.startswith("wb.")
        ):
            return True
        return href_host == base_host
    except Exception:
        return True


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _money_to_int(value: Any) -> int | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not digits:
        return None
    number = int(digits)
    return number if number > 0 else None


def _extract_script(source: str) -> str:
    return r"""
    ({source}) => {
      const pickContainer = (a) => {
        let node = a;
        let best = a;
        for (let i = 0; i < 6 && node; i += 1) {
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
          extraction_method: 'dom_listing'
        });
      }
      return out;
    }
    """.strip()


def _json_loads_maybe(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def _iter_ozon_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    widget_states = payload.get("widgetStates") or {}
    if not isinstance(widget_states, dict):
        return items
    for key, raw_state in widget_states.items():
        if not any(hint in str(key) for hint in _OZON_TILE_WIDGET_HINTS):
            raw_text = str(raw_state)
            if not any(hint in raw_text for hint in _OZON_TILE_WIDGET_HINTS):
                continue
        state = _json_loads_maybe(raw_state)
        if not isinstance(state, dict):
            continue
        state_items = state.get("items") or []
        if isinstance(state_items, list):
            for item in state_items:
                if isinstance(item, dict):
                    items.append(item)
    return items


def _iter_ozon_main_state(item: dict[str, Any]) -> list[dict[str, Any]]:
    state = item.get("mainState") or []
    return state if isinstance(state, list) else []


def _ozon_price_from_item(item: dict[str, Any]) -> tuple[int | None, int | None, list[str]]:
    actual_prices: list[int] = []
    original_prices: list[int] = []
    seen_texts: list[str] = []
    for state in _iter_ozon_main_state(item):
        price_v2 = state.get("priceV2") if isinstance(state, dict) else None
        if not isinstance(price_v2, dict):
            continue
        for price_obj in price_v2.get("price") or []:
            if not isinstance(price_obj, dict):
                continue
            text = _clean_text(price_obj.get("text"))
            if not text:
                continue
            seen_texts.append(text)
            lower = text.lower()
            if "мес" in lower or "×" in lower or " x " in lower:
                continue
            number = _money_to_int(text)
            if not number or number < 1000:
                continue
            style = str(price_obj.get("textStyle") or "").upper()
            if "ORIGINAL" in style:
                original_prices.append(number)
            else:
                actual_prices.append(number)
    return (min(actual_prices) if actual_prices else None, min(original_prices) if original_prices else None, seen_texts)


def _ozon_title_from_item(item: dict[str, Any]) -> str:
    for state in _iter_ozon_main_state(item):
        if not isinstance(state, dict):
            continue
        text_atom = state.get("textAtom")
        if isinstance(text_atom, dict) and (state.get("id") == "name" or text_atom.get("testInfo", {}).get("automatizationId") == "tile-name"):
            title = _clean_text(text_atom.get("text"))
            if title:
                return title
    for state in _iter_ozon_main_state(item):
        if not isinstance(state, dict):
            continue
        text_atom = state.get("textAtom")
        if isinstance(text_atom, dict):
            title = _clean_text(text_atom.get("text"))
            if title:
                return title
    return ""


def _ozon_brand_from_item(item: dict[str, Any]) -> str:
    for state in _iter_ozon_main_state(item):
        if not isinstance(state, dict):
            continue
        for block_key in ("labelListV2", "labelList"):
            block = state.get(block_key)
            if not isinstance(block, dict):
                continue
            for label_item in block.get("items") or []:
                if not isinstance(label_item, dict):
                    continue
                text = ""
                if isinstance(label_item.get("text"), dict):
                    text = _clean_text(label_item["text"].get("text"))
                else:
                    text = _clean_text(label_item.get("title"))
                if text and text.upper() == "DEMIAND":
                    return text
    return ""


def _ozon_stock_from_item(item: dict[str, Any]) -> int | None:
    multi = item.get("multiButton") or {}
    ozon_button = multi.get("ozonButton") if isinstance(multi, dict) else None
    add_to_cart = ozon_button.get("addToCart") if isinstance(ozon_button, dict) else None
    if isinstance(add_to_cart, dict):
        qbtn = add_to_cart.get("quantityButton")
        if isinstance(qbtn, dict) and qbtn.get("maxItems") is not None:
            try:
                return int(qbtn.get("maxItems") or 0)
            except Exception:
                pass
    for state in _iter_ozon_main_state(item):
        if not isinstance(state, dict):
            continue
        label = state.get("labelList")
        if not isinstance(label, dict):
            continue
        for label_item in label.get("items") or []:
            title = _clean_text(label_item.get("title") if isinstance(label_item, dict) else "")
            if "шт" in title and "остал" in title.lower():
                number = _money_to_int(title)
                if number is not None:
                    return number
    return None


def _ozon_eta_from_item(item: dict[str, Any]) -> str | None:
    multi = item.get("multiButton") or {}
    ozon_button = multi.get("ozonButton") if isinstance(multi, dict) else None
    add_to_cart = ozon_button.get("addToCart") if isinstance(ozon_button, dict) else None
    if isinstance(add_to_cart, dict):
        title = _clean_text(add_to_cart.get("title"))
        if title:
            return title
    return None


def _ozon_image_from_item(item: dict[str, Any]) -> str:
    tile_image = item.get("tileImage") or {}
    images = tile_image.get("items") if isinstance(tile_image, dict) else []
    if not isinstance(images, list):
        return ""
    for img_item in images:
        if not isinstance(img_item, dict):
            continue
        image = img_item.get("image")
        if isinstance(image, dict):
            link = _clean_text(image.get("link"))
            if link:
                return link
    return ""


def _ozon_card_from_item(item: dict[str, Any], *, seed: dict[str, Any], page_url: str, page_index: int | None) -> dict[str, Any] | None:
    title = _ozon_title_from_item(item)
    brand = _ozon_brand_from_item(item)
    price, old_price, price_texts = _ozon_price_from_item(item)
    action = item.get("action") if isinstance(item.get("action"), dict) else {}
    raw_link = action.get("link") or ""
    href = urljoin("https://ozon.kz", str(raw_link)) if raw_link else ""
    sku = str(item.get("sku") or item.get("id") or "").strip()
    if not title or not href or "/product/" not in href or not price:
        return None
    if str(seed.get("brand") or "").upper() and str(seed.get("brand") or "").upper() not in (title + " " + brand).upper():
        return None
    stock = _ozon_stock_from_item(item)
    eta_text = _ozon_eta_from_item(item)
    image = _ozon_image_from_item(item)
    text_parts = [title, brand, f"{price} ₸"]
    if old_price:
        text_parts.append(f"old {old_price} ₸")
    if stock is not None:
        text_parts.append(f"{stock} шт осталось")
    if eta_text:
        text_parts.append(eta_text)
    return {
        "href": href,
        "link_text": title,
        "aria_label": title,
        "image": image,
        "image_alt": title,
        "container_text": "\n".join(text_parts),
        "html": "",
        "source": "ozon",
        "seed_key": seed.get("seed_key"),
        "seed_url": seed.get("url"),
        "market_id": sku or href,
        "title": title,
        "brand": brand or seed.get("brand"),
        "price": price,
        "old_price": old_price,
        "price_texts": price_texts,
        "stock": stock if stock is not None else 1,
        "available": stock is None or stock > 0,
        "eta_text": eta_text,
        "url": href,
        "extraction_method": "ozon_entrypoint_json",
        "page_url": page_url,
        "page_index": page_index,
    }


def _ozon_meta_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    shared = _json_loads_maybe(payload.get("shared"))
    if isinstance(shared, dict):
        catalog = shared.get("catalog") if isinstance(shared.get("catalog"), dict) else {}
        meta["total_pages"] = shared.get("totalPages")
        meta["current_page"] = shared.get("currentPage")
        if isinstance(catalog, dict):
            meta["category_id"] = (catalog.get("category") or {}).get("id") if isinstance(catalog.get("category"), dict) else None
    page_info = payload.get("pageInfo") if isinstance(payload.get("pageInfo"), dict) else {}
    if page_info:
        meta["page_url"] = page_info.get("url")
        analytics = page_info.get("analyticsInfo") if isinstance(page_info.get("analyticsInfo"), dict) else {}
        meta["brand_id"] = analytics.get("brandId")
        meta["category_id"] = meta.get("category_id") or analytics.get("categoryId")
    meta["next_page"] = payload.get("nextPage")
    meta["prev_page"] = payload.get("prevPage")
    return meta


def _extract_ozon_payload_cards(payload: dict[str, Any], *, seed: dict[str, Any], page_url: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    meta = _ozon_meta_from_payload(payload)
    page_index = meta.get("current_page")
    cards: list[dict[str, Any]] = []
    for item in _iter_ozon_items(payload):
        card = _ozon_card_from_item(item, seed=seed, page_url=page_url, page_index=page_index if isinstance(page_index, int) else None)
        if card:
            cards.append(card)
    meta["cards_from_payload"] = len(cards)
    return cards, meta


def _ozon_entrypoint_url(base_url: str, relative_url: str) -> str:
    return f"{base_url.rstrip('/')}{_OZON_ENTRYPOINT_MARKER}?url={quote(relative_url, safe='')}"


def _fetch_ozon_entrypoint_pages(page: Any, seed: dict[str, Any], report: dict[str, Any]) -> list[dict[str, Any]]:
    base = "https://ozon.kz"
    first_url = str(seed.get("url") or "").strip()
    relative = urlparse(first_url).path or "/"
    if urlparse(first_url).query:
        relative = f"{relative}?{urlparse(first_url).query}"

    cards_by_url: dict[str, dict[str, Any]] = {}
    seen_relatives: set[str] = set()
    next_relative = relative
    max_pages = 12
    payload_pages = 0
    report.setdefault("ozon_entrypoint_pages", [])

    for _ in range(max_pages):
        if not next_relative or next_relative in seen_relatives:
            break
        seen_relatives.add(next_relative)
        endpoint = _ozon_entrypoint_url(base, next_relative)
        try:
            response_text = page.evaluate(
                """async (url) => {
                    const res = await fetch(url, {credentials: 'include'});
                    const text = await res.text();
                    return JSON.stringify({status: res.status, url: res.url, text});
                }""",
                endpoint,
            )
            response = json.loads(response_text)
        except Exception as exc:
            report.setdefault("errors", []).append(f"ozon_entrypoint_fetch_failed: {exc}")
            break
        status = int(response.get("status") or 0)
        text = str(response.get("text") or "")
        page_item: dict[str, Any] = {"relative_url": next_relative, "status_code": status, "cards": 0}
        if status != 200:
            page_item["error"] = f"status_{status}"
            report["ozon_entrypoint_pages"].append(page_item)
            break
        try:
            payload = json.loads(text)
        except Exception as exc:
            page_item["error"] = f"bad_json: {exc}"
            page_item["text_head"] = text[:120]
            report["ozon_entrypoint_pages"].append(page_item)
            break
        page_cards, meta = _extract_ozon_payload_cards(payload, seed=seed, page_url=next_relative)
        payload_pages += 1
        for card in page_cards:
            href = str(card.get("href") or card.get("url") or "")
            if href and href not in cards_by_url:
                cards_by_url[href] = card
        page_item.update({
            "cards": len(page_cards),
            "current_page": meta.get("current_page"),
            "total_pages": meta.get("total_pages"),
            "next_page_present": bool(meta.get("next_page")),
        })
        report["ozon_entrypoint_pages"].append(page_item)
        next_page = str(meta.get("next_page") or "")
        if not next_page:
            break
        next_relative = next_page
    report["ozon_entrypoint_payload_pages"] = payload_pages
    report["cards_from_ozon_entrypoint"] = len(cards_by_url)
    return list(cards_by_url.values())


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
        "cards_from_ozon_entrypoint": 0,
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

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=bool(cfg.get("headless", True)))
            context = browser.new_context(
                viewport={"width": int(cfg.get("viewport_width") or 1440), "height": int(cfg.get("viewport_height") or 1400)},
                locale="ru-RU",
                timezone_id="Asia/Almaty",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=int(cfg.get("goto_timeout_ms") or 60000))
            page.wait_for_timeout(int(cfg.get("wait_after_open_ms") or 3000))

            if source == "ozon":
                for raw in _fetch_ozon_entrypoint_pages(page, seed, report):
                    href = str(raw.get("href") or raw.get("url") or "")
                    if href and href not in cards_by_url:
                        cards_by_url[href] = raw
                if len(cards_by_url) >= max_cards:
                    report["cards_seen_raw"] = len(cards_by_url)
                    report["cards_unique_url"] = len(cards_by_url)
                    browser.close()
                    report["status"] = "ok" if cards_by_url else "empty"
                    return list(cards_by_url.values()), report

            for round_idx in range(max_rounds + 1):
                raw_cards = page.evaluate(_extract_script(source), source)
                before = len(cards_by_url)
                dom_added = 0
                for raw in raw_cards or []:
                    href = str(raw.get("href") or "")
                    if not href or not _is_product_url(source, href) or not _same_domain(url, href):
                        continue
                    if href not in cards_by_url:
                        raw.update({"seed_key": seed.get("seed_key"), "source": source, "seed_url": url})
                        cards_by_url[href] = raw
                        dom_added += 1
                    if len(cards_by_url) >= max_cards:
                        break
                report["cards_from_dom"] = int(report.get("cards_from_dom") or 0) + dom_added

                report["scroll_rounds"] = round_idx
                if len(cards_by_url) == before:
                    no_new += 1
                else:
                    no_new = 0
                if len(cards_by_url) >= max_cards or no_new >= no_new_limit:
                    break
                page.mouse.wheel(0, int(cfg.get("scroll_step_px") or 1200))
                page.wait_for_timeout(int(cfg.get("scroll_wait_ms") or 1200))
            browser.close()
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append(str(exc))
        return list(cards_by_url.values()), report

    report["cards_seen_raw"] = len(cards_by_url)
    report["cards_unique_url"] = len(cards_by_url)
    expected_min = int(seed.get("expected_min_cards") or 0)
    if expected_min and len(cards_by_url) < expected_min:
        report["warnings"].append(f"cards_below_expected_min: expected_min={expected_min}, found={len(cards_by_url)}")
    report["status"] = "ok" if cards_by_url else "empty"
    return list(cards_by_url.values()), report
