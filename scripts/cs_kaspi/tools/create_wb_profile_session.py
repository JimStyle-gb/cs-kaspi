from __future__ import annotations

import base64
import json
from pathlib import Path

PROFILE_DIR = Path("input/private")
STATE_JSON = PROFILE_DIR / "wb_storage_state.json"
STATE_B64 = PROFILE_DIR / "wb_storage_state.b64.txt"
WB_URL = "https://www.wildberries.ru/"


def _to_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def run() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise SystemExit(f"Playwright не установлен: {exc}")

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(
            viewport={"width": 1440, "height": 1400},
            locale="ru-KZ",
            timezone_id="Asia/Almaty",
            geolocation={"latitude": 43.238949, "longitude": 76.889709},
            permissions=["geolocation"],
            extra_http_headers={"Accept-Language": "ru-KZ,ru;q=0.9,en-US;q=0.7,en;q=0.6"},
        )
        page = context.new_page()
        page.goto(WB_URL, wait_until="domcontentloaded", timeout=60000)
        print("\nОткрылся браузер WB.")
        print("1) Войди в отдельный рабочий WB-профиль.")
        print("2) Укажи город доставки: Алматы.")
        print("3) Убедись, что цены в ₸.")
        print("4) Открой любую seed-ссылку Demiand и проверь, что товары видны.")
        input("\nКогда всё готово, вернись в консоль и нажми Enter... ")
        context.storage_state(path=str(STATE_JSON))
        browser.close()

    # Validate before writing b64.
    data = json.loads(STATE_JSON.read_text(encoding="utf-8"))
    cookies = data.get("cookies") or []
    if not cookies:
        raise SystemExit("Сессия сохранилась без cookies. Повтори вход в WB и попробуй ещё раз.")
    STATE_B64.write_text(_to_b64(STATE_JSON), encoding="utf-8")
    print(f"\nГотово: {STATE_JSON}")
    print(f"Готово: {STATE_B64}")
    print("\nСодержимое wb_storage_state.b64.txt нужно добавить в GitHub Secret WB_STORAGE_STATE_B64.")
    print("Эти файлы приватные. Не коммить их в репозиторий.")


if __name__ == "__main__":
    run()
