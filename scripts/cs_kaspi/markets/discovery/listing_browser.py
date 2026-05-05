from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - Playwright is optional at import time.
    sync_playwright = None

from scripts.cs_kaspi.core.paths import path_from_config

from .seed_config import cfg as market_cfg


WB_BRAND_ID_DEMIAND = 53038
WB_DEST_ALMATY = "233"
WB_CURRENCY = "kzt"


_BASKET_LIMITS = [
    (143, 1), (287, 2), (431, 3), (719, 4), (1007, 5), (1061, 6), (1115, 7), (1169, 8),
    (1313, 9), (1601, 10), (1655, 11), (1919, 12), (2045, 13), (2189, 14), (2405, 15),
    (2621, 16), (2837, 17), (3053, 18), (3269, 19), (3485, 20), (3701, 21), (3917, 22),
    (4133, 23), (4349, 24), (4565, 25), (4879, 26), (5183, 27), (5507, 28), (5823, 29),
    (6005, 30), (6323, 31), (6641, 32), (6960, 33), (7280, 34), (7600, 35),
]


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


def _normalize_spaces(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        digits = re.sub(r"\D+", "", value)
        return int(digits) if digits else None
    return None


def _wb_money(value: Any) -> int | None:
    amount = _as_int(value)
    if amount is None or amount <= 0:
        return None
    # WB API returns KZT in kopeck-like units, e.g. 10903000 = 109 030 ₸.
    if amount >= 100000:
        return int(round(amount / 100))
    return amount


def _force_wb_api_params(url: str, seed: dict[str, Any]) -> str:
    api_cfg = (market_cfg().get("wb_api", {}) or {})
    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params["curr"] = str(seed.get("currency") or api_cfg.get("currency") or WB_CURRENCY).lower()
    params["dest"] = str(seed.get("dest") or api_cfg.get("dest") or WB_DEST_ALMATY)
    params["locale"] = str(seed.get("locale") or api_cfg.get("locale") or "kz").lower()
    params["lang"] = str(seed.get("lang") or api_cfg.get("lang") or "ru").lower()
    params["fbrand"] = str(seed.get("brand_id") or api_cfg.get("brand_id") or WB_BRAND_ID_DEMIAND)
    params.setdefault("appType", "1")
    params.setdefault("resultset", "catalog")
    params.setdefault("sort", "popular")
    params.setdefault("spp", "30")
    query = urlencode(params, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, parsed.fragment))


def _decode_json_response(text: str) -> Any:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("empty WB API response")
    if raw[0] not in "[{":
        first_obj = min([i for i in (raw.find("{"), raw.find("[")) if i >= 0], default=-1)
        if first_obj >= 0:
            raw = raw[first_obj:]
    return json.loads(raw)


def _looks_like_product(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    return item.get("id") is not None and item.get("name") is not None and (item.get("brand") or item.get("brandId"))


def _product_lists(obj: Any) -> list[list[dict[str, Any]]]:
    found: list[list[dict[str, Any]]] = []
    stack: list[Any] = [obj]
    seen = 0
    while stack and seen < 12000:
        seen += 1
        cur = stack.pop()
        if isinstance(cur, dict):
            products = cur.get("products")
            if isinstance(products, list) and any(_looks_like_product(x) for x in products):
                found.append([x for x in products if isinstance(x, dict)])
            for value in cur.values():
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(cur, list):
            stack.extend(cur[:500])
    found.sort(key=len, reverse=True)
    return found


def _extract_total(obj: Any) -> int | None:
    if isinstance(obj, dict):
        total = _as_int(obj.get("total"))
        if total is not None:
            return total
        metadata = obj.get("metadata")
        if isinstance(metadata, dict):
            total = _as_int(metadata.get("total"))
            if total is not None:
                return total
    return None


def _first_size(product: dict[str, Any]) -> dict[str, Any]:
    sizes = product.get("sizes")
    if isinstance(sizes, list):
        for item in sizes:
            if isinstance(item, dict):
                return item
    return {}


def _price_from_product(product: dict[str, Any]) -> tuple[int | None, int | None]:
    size = _first_size(product)
    price = size.get("price") if isinstance(size.get("price"), dict) else product.get("price")
    if isinstance(price, dict):
        current = _wb_money(price.get("product") or price.get("total") or price.get("sale") or price.get("price"))
        old = _wb_money(price.get("basic") or price.get("old") or price.get("base"))
        return current, old
    for key in ("salePriceU", "priceU", "salePrice", "price"):
        current = _wb_money(product.get(key))
        if current:
            return current, None
    return None, None


def _stock_from_product(product: dict[str, Any]) -> int | None:
    total = _as_int(product.get("totalQuantity") or product.get("quantity") or product.get("qty"))
    if total is not None:
        return max(0, total)
    qty = 0
    found = False
    for size in product.get("sizes") or []:
        if not isinstance(size, dict):
            continue
        for stock in size.get("stocks") or []:
            if isinstance(stock, dict):
                value = _as_int(stock.get("qty"))
                if value is not None:
                    qty += max(0, value)
                    found = True
    return qty if found else None


def _time2_hours(product: dict[str, Any]) -> int | None:
    size = _first_size(product)
    for source in (size, product):
        value = _as_int(source.get("time2") if isinstance(source, dict) else None)
        if value is not None and value > 0:
            return value
    return None


def _lead_days_from_time2(product: dict[str, Any]) -> int | None:
    hours = _time2_hours(product)
    if hours is None:
        return None
    # WB time2 is hour-like logistics value. Round to the nearest day and do not add any safety buffer.
    return max(1, int(round(hours / 24)))


def _eta_text_from_days(days: int | None) -> str | None:
    if days is None:
        return None
    if days == 0:
        return "сегодня"
    if days == 1:
        return "завтра"
    if days == 2:
        return "послезавтра"
    return f"{days} дней"


def _colors_text(product: dict[str, Any]) -> str:
    values: list[str] = []
    colors = product.get("colors")
    if isinstance(colors, list):
        for color in colors:
            if isinstance(color, dict):
                name = _normalize_spaces(color.get("name"))
                if name and name not in values:
                    values.append(name)
    return ", ".join(values)


def _basket_num(nm_id: int) -> int:
    vol = nm_id // 100000
    for limit, basket in _BASKET_LIMITS:
        if vol <= limit:
            return basket
    return 36


def _image_url(nm_id: int, pics: Any) -> str:
    if _as_int(pics) in (None, 0):
        return ""
    vol = nm_id // 100000
    part = nm_id // 1000
    basket = _basket_num(nm_id)
    return f"https://basket-{basket:02}.wbbasket.ru/vol{vol}/part{part}/{nm_id}/images/big/1.webp"


def _is_expected_brand(product: dict[str, Any], expected_brand: str) -> bool:
    brand = _normalize_spaces(product.get("brand"))
    brand_id = _as_int(product.get("brandId"))
    supplier = _normalize_spaces(product.get("supplier"))
    expected = _normalize_spaces(expected_brand or "DEMIAND").lower()
    return (
        brand.lower() == expected
        or supplier.lower() == expected
        or brand_id == WB_BRAND_ID_DEMIAND
        or "demiand" in f"{brand} {supplier} {_normalize_spaces(product.get('name'))}".lower()
    )


def _card_from_product(product: dict[str, Any], seed: dict[str, Any], api_url: str) -> dict[str, Any] | None:
    if not _is_expected_brand(product, str(seed.get("brand") or "DEMIAND")):
        return None
    product_id = _as_int(product.get("id") or product.get("nmId"))
    name = _normalize_spaces(product.get("name"))
    if not product_id or not name:
        return None
    brand = _normalize_spaces(product.get("brand") or seed.get("brand") or "DEMIAND") or "DEMIAND"
    title = name if brand.lower() in name.lower() else f"{brand} {name}"
    price, old_price = _price_from_product(product)
    stock = _stock_from_product(product)
    lead_days = _lead_days_from_time2(product)
    eta_text = _eta_text_from_days(lead_days)
    colors = _colors_text(product)
    entity = _normalize_spaces(product.get("entity"))
    url = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"
    lines = [
        title,
        f"{price} ₸" if price else "",
        f"Старая цена: {old_price} ₸" if old_price else "",
        f"Остаток WB: {stock} шт" if stock is not None else "",
        f"Срок WB: {eta_text}" if eta_text else "",
        f"Тип WB: {entity}" if entity else "",
        f"Цвет WB: {colors}" if colors else "",
        f"Рейтинг WB: {product.get('reviewRating') or product.get('nmReviewRating')}" if product.get("reviewRating") or product.get("nmReviewRating") else "",
        f"Отзывы WB: {product.get('feedbacks') or product.get('nmFeedbacks')}" if product.get("feedbacks") or product.get("nmFeedbacks") else "",
    ]
    return {
        "source": seed.get("source") or "wb",
        "seed_key": seed.get("seed_key"),
        "seed_url": seed.get("url"),
        "api_url": api_url,
        "href": url,
        "url": url,
        "market_id": str(product_id),
        "link_text": title,
        "aria_label": title,
        "title": title,
        "brand": brand,
        "brand_id": product.get("brandId"),
        "supplier": product.get("supplier"),
        "supplier_id": product.get("supplierId"),
        "entity": entity,
        "wb_entity": entity,
        "subject_id": product.get("subjectId"),
        "subject_parent_id": product.get("subjectParentId"),
        "wb_root": product.get("root"),
        "wb_kind_id": product.get("kindId"),
        "wb_match_id": product.get("matchId"),
        "wb_volume": product.get("volume"),
        "wb_weight": product.get("weight"),
        "color_text": colors,
        "market_color_raw": colors,
        "price": price,
        "old_price": old_price,
        "price_currency": "KZT" if price else None,
        "stock": stock,
        "available": False if stock == 0 else bool(price),
        "eta_text": eta_text,
        "lead_time_days": lead_days,
        "wb_time1": product.get("time1") or _first_size(product).get("time1"),
        "wb_time2": product.get("time2") or _first_size(product).get("time2"),
        "image": _image_url(product_id, product.get("pics")),
        "image_alt": title,
        "container_text": "\n".join(x for x in lines if x),
        "html": "",
        "extract_method": "wb_json_api_products_dest_233_kzt",
        "raw_wb": {
            "id": product.get("id"),
            "root": product.get("root"),
            "brand": product.get("brand"),
            "brandId": product.get("brandId"),
            "name": product.get("name"),
            "entity": product.get("entity"),
            "subjectId": product.get("subjectId"),
            "subjectParentId": product.get("subjectParentId"),
            "totalQuantity": product.get("totalQuantity"),
            "colors": product.get("colors"),
            "sizes": product.get("sizes"),
            "time1": product.get("time1"),
            "time2": product.get("time2"),
            "pics": product.get("pics"),
            "feedbacks": product.get("feedbacks"),
            "reviewRating": product.get("reviewRating"),
            "nmReviewRating": product.get("nmReviewRating"),
            "supplierId": product.get("supplierId"),
            "supplierRating": product.get("supplierRating"),
            "matchId": product.get("matchId"),
            "volume": product.get("volume"),
            "weight": product.get("weight"),
            "kindId": product.get("kindId"),
        },
    }


def _api_response_has_products(text: str) -> bool:
    raw = text or ""
    return "products" in raw and ("DEMIAND" in raw or "brandId" in raw or "brand" in raw)


def _fetch_json_direct(url: str, seed: dict[str, Any], timeout: int) -> tuple[Any, str, int]:
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "ru-KZ,ru;q=0.9,en-US;q=0.7,en;q=0.6",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "referer": str(seed.get("url") or "https://www.wildberries.ru/"),
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    text = response.text or ""
    response.raise_for_status()
    return _decode_json_response(text), text, response.status_code


def _fetch_json_browser(url: str, seed: dict[str, Any], timeout: int) -> tuple[Any, str, int, str]:
    if sync_playwright is None:
        raise RuntimeError("playwright_is_not_available")

    seed_key = seed.get("seed_key") or seed.get("url") or "seed"
    browser_timeout_ms = max(20000, int(timeout * 1000))
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    captured: list[tuple[str, str, int]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = browser.new_context(
            locale="ru-KZ",
            timezone_id="Asia/Almaty",
            geolocation={"latitude": 43.238949, "longitude": 76.889709},
            permissions=["geolocation"],
            viewport={"width": 1440, "height": 1400},
            user_agent=user_agent,
            extra_http_headers={
                "accept-language": "ru-KZ,ru;q=0.9,en-US;q=0.7,en;q=0.6",
            },
        )
        page = context.new_page()

        def on_response(response: Any) -> None:
            try:
                response_url = str(response.url or "")
                if "/__internal/search/" not in response_url and "/search/" not in response_url:
                    return
                if "fbrand=53038" not in response_url and "brand=53038" not in response_url:
                    return
                if response.status != 200:
                    return
                body = response.text()
                if _api_response_has_products(body):
                    captured.append((response_url, body, int(response.status)))
            except Exception:
                return

        page.on("response", on_response)

        try:
            page.goto(str(seed.get("url") or "https://www.wildberries.ru/"), wait_until="domcontentloaded", timeout=browser_timeout_ms)
            page.wait_for_timeout(2500)
            for _ in range(10):
                page.mouse.wheel(0, 1400)
                page.wait_for_timeout(450)
            try:
                _write_debug(seed_key, "browser_page.html", page.content()[:2_000_000])
                _write_debug(seed_key, "browser_screenshot.png", page.screenshot(full_page=True))
            except Exception:
                pass

            best_captured: tuple[str, str, int] | None = None
            best_count = -1
            for response_url, body, status in captured:
                try:
                    parsed = _decode_json_response(body)
                    lists = _product_lists(parsed)
                    count = len(lists[0]) if lists else 0
                except Exception:
                    count = 0
                if count > best_count:
                    best_count = count
                    best_captured = (response_url, body, status)
            if best_captured and best_count > 0:
                response_url, body, status = best_captured
                _write_debug(seed_key, "browser_api_url.txt", response_url)
                return _decode_json_response(body), body, status, "browser_captured_response"

            result = page.evaluate(
                """async (apiUrl) => {
                    const response = await fetch(apiUrl, {
                        method: 'GET',
                        credentials: 'include',
                        headers: {
                            'accept': 'application/json, text/plain, */*',
                            'cache-control': 'no-cache',
                            'pragma': 'no-cache'
                        }
                    });
                    const text = await response.text();
                    return {status: response.status, url: response.url, text};
                }""",
                url,
            )
            status = int(result.get("status") or 0)
            text = str(result.get("text") or "")
            _write_debug(seed_key, "browser_fetch_status.txt", f"{status} {result.get('url') or url}")
            if status >= 400:
                _write_debug(seed_key, "browser_fetch_error_body.txt", text[:5000])
                raise requests.HTTPError(f"browser_fetch_http_{status}")
            return _decode_json_response(text), text, status, "browser_fetch_after_seed_page"
        finally:
            context.close()
            browser.close()


def _fetch_json(url: str, seed: dict[str, Any], timeout: int) -> tuple[Any, str, int, str]:
    browser_error = ""
    try:
        return _fetch_json_browser(url, seed, timeout)
    except Exception as exc:
        browser_error = str(exc)

    try:
        data, text, status = _fetch_json_direct(url, seed, timeout)
        return data, text, status, "direct_requests_after_browser_failed"
    except Exception as exc:
        direct_error = str(exc)
        raise RuntimeError(f"browser_failed: {browser_error}; direct_failed: {direct_error}") from exc


def fetch_seed(seed: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    seed_key = seed.get("seed_key") or seed.get("url") or "seed"
    api_cfg = (market_cfg().get("wb_api", {}) or {})
    api_url = str(seed.get("api_url") or "").strip()
    report: dict[str, Any] = {
        "seed_key": seed.get("seed_key"),
        "source": seed.get("source") or "wb",
        "url": seed.get("url"),
        "api_url_configured": bool(api_url),
        "fetch_mode": "wb_json_api_products_browser_then_direct",
        "status": "pending",
        "errors": [],
        "warnings": [],
        "cards_unique_url": 0,
        "cards_seen_raw": 0,
        "cards_from_api": 0,
        "api_total": None,
        "price_currency_detected": "kzt",
        "delivery_region_detected": "almaty_dest_233",
        "wb_dest": str(seed.get("dest") or api_cfg.get("dest") or WB_DEST_ALMATY),
        "wb_locale": str(seed.get("locale") or api_cfg.get("locale") or "kz"),
        "scroll_rounds": 0,
    }
    if not api_url:
        report["status"] = "failed"
        report["errors"].append("missing_wb_api_url_in_seed_config")
        return [], report

    forced_url = _force_wb_api_params(api_url, seed)
    report["api_url_used"] = forced_url
    _write_debug(seed_key, "api_url.txt", forced_url)

    timeout = int(api_cfg.get("request_timeout_sec") or 45)
    retries = int(api_cfg.get("max_retries") or 2)
    polite_sleep = float(api_cfg.get("polite_sleep_sec") or 0)
    data: Any = None
    raw_text = ""
    last_error = ""

    for attempt in range(retries + 1):
        try:
            data, raw_text, status_code, fetch_method = _fetch_json(forced_url, seed, timeout)
            report["http_status"] = status_code
            report["fetch_method"] = fetch_method
            break
        except Exception as exc:
            last_error = str(exc)
            if attempt < retries:
                time.sleep(max(0.2, polite_sleep))
            else:
                report["status"] = "failed"
                report["errors"].append(f"wb_api_request_failed: {last_error}")
                _write_debug(seed_key, "api_error.txt", last_error)
                return [], report

    _write_debug(seed_key, "api_response.json", raw_text[:2_000_000])
    product_lists = _product_lists(data)
    products = product_lists[0] if product_lists else []
    total = _extract_total(data)
    report["api_total"] = total
    report["api_product_lists_found"] = len(product_lists)
    report["api_products_returned"] = len(products)
    if total is not None and len(products) and total > len(products):
        report["warnings"].append(f"wb_api_total_{total}_greater_than_returned_products_{len(products)}_using_returned_products_only")

    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    max_cards = int((market_cfg().get("discovery", {}) or {}).get("max_cards_per_seed") or 1200)
    for product in products:
        card = _card_from_product(product, seed, forced_url)
        if not card:
            continue
        key = str(card.get("url") or card.get("market_id") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        cards.append(card)
        if len(cards) >= max_cards:
            report["warnings"].append(f"max_cards_per_seed_reached_{max_cards}")
            break

    report["cards_from_api"] = len(cards)
    report["cards_seen_raw"] = len(cards)
    report["cards_unique_url"] = len(cards)
    if cards:
        report["status"] = "ok"
    else:
        report["status"] = "empty"
        report["warnings"].append("wb_api_returned_no_demiand_cards")
    return cards, report
