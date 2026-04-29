from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from .seed_config import browser_cfg, discovery_cfg

_PRODUCT_URL_MARKERS = {
    "ozon": ("/product/",),
    "wb": ("/catalog/", "/detail"),
}


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
        return not href_host or href_host == base_host
    except Exception:
        return True


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
          html: box ? box.outerHTML.slice(0, 3000) : ''
        });
      }
      return out;
    }
    """.strip()


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

            for round_idx in range(max_rounds + 1):
                raw_cards = page.evaluate(_extract_script(source), source)
                before = len(cards_by_url)
                for raw in raw_cards or []:
                    href = str(raw.get("href") or "")
                    if not href or not _is_product_url(source, href) or not _same_domain(url, href):
                        continue
                    if href not in cards_by_url:
                        raw.update({"seed_key": seed.get("seed_key"), "source": source, "seed_url": url})
                        cards_by_url[href] = raw
                    if len(cards_by_url) >= max_cards:
                        break

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
