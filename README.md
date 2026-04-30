# CS-Kaspi v7.0 WB-only clean

CS-Kaspi — GitHub-only проект для подготовки уникальных VAITAN-карточек Kaspi на основе официальной технической информации поставщика и реальных товарных предложений WB.

## Главная логика

- **Official source** — справочник полной технической и SEO-информации: бренд, модель, артикул, описание, характеристики, фото.
- **WB seed listing** — единственный market-source для реального продаваемого предложения: title, url, price, stock, ETA, цвет, комплект, набор.
- **Рабочий market-source только WB**.
- **Нет ручного market input**: проект не ждёт CSV, а сам собирает WB listing по seed-ссылкам.
- **Нет fallback-поиска**: проект работает только по seed-ссылкам, которые дал пользователь.
- **Нет product-page-first**: карточки WB не открываются по умолчанию; парсится listing с прокруткой и сетевыми JSON-ответами WB.
- **Одинаковые варианты схлопываются**: если один и тот же вариант найден несколько раз, берётся самая низкая цена.
- **Цена Kaspi** = самая низкая WB source price + 30%, затем последние две цифры обрезаются до `00` вниз. Пример: `199485 -> 199400`.
- **Срок WB переносится без safety buffer**.
- **Kaspi live-send отключён**: проект готовит только preview, draft API JSON и draft XML.

## Структура

```text
config/                  настройки проекта, Kaspi, поставщиков и WB seed-ссылок
scripts/                 код пайплайна
artifacts/               результаты сборки: raw cache, state, market_discovery, preview, exports, reports
.github/workflows/       GitHub Actions, главный workflow Build_All
```

## Основной workflow Build_All

1. `refresh_official_sources` — скачать официальный справочник поставщика и raw-cache в `artifacts/raw/official/`.
2. `discover_market_data` — открыть WB seed-listings, прокрутить страницы и собрать видимые товары.
3. `refresh_market_data` — построить market-state из найденных sellable variants.
4. `refresh_kaspi_matches` — прочитать state существующих товаров Kaspi, когда позже будет добавлен API-sync; сейчас безопасно возвращает пустой match-state.
5. `build_master_catalog` — собрать official + market + kaspi_match в единый catalog.
6. `build_preview` — предпросмотр будущих VAITAN-карточек.
7. `build_kaspi_exports` — разделить товары на create/update/pause/skipped.
8. `build_kaspi_delivery` — подготовить draft API payload и draft XML.
9. `check_project` — итоговые проверки и Telegram summary.
10. `send_telegram_report` — отправить Telegram-отчёт, если заданы secrets.

## Где менять WB ссылки

Файл:

```text
config/market_sources.yml
```

Там указываются только готовые WB seed-ссылки. Если ссылка упала или товаров меньше нормы, проект не ищет запасные варианты, а пишет проблему в отчёт и Telegram.

## Что смотреть после прогона

```text
artifacts/market_discovery/seed_url_report.txt
artifacts/market_discovery/market_discovery_report.txt
artifacts/state/master_catalog_summary.json
artifacts/preview/kaspi_preview.txt
artifacts/exports/kaspi_export_summary.json
artifacts/exports/kaspi_delivery_preview.txt
artifacts/reports/check_project_report.txt
artifacts/reports/telegram_summary.txt
```

## Безопасность

Проект не отправляет товары в Kaspi. Все live-настройки отключены в `config/kaspi.yml`.
