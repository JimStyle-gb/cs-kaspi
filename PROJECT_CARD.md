# Project card: CS-Kaspi v6.1

## Цель

Создавать и обновлять собственные уникальные карточки Kaspi под VAITAN, не прикрепляясь к чужим карточкам.

## Финальная бизнес-формула

```text
Official-site = справочник модели и SEO
Ozon/WB seed-listings = реальные предложения, цены, сроки и комплектации
Market variant = уникальный продаваемый вариант
Kaspi candidate = наша VAITAN-карточка
```

## Важные правила

1. Official-сайт не является списком exact-offers для обязательного совпадения один-в-один.
2. Official-сайт нужен как справочник: модель, характеристики, описание, фото, SEO.
3. Ozon/WB seed-ссылки, которые дал пользователь, являются основным источником sellable market offers.
4. Проект не делает автоматический fallback search по бренду или модели.
5. Проект не открывает карточки Ozon/WB как основной процесс.
6. Listing парсится через браузерную прокрутку, потому что Ozon/WB подгружают товары lazy/infinite-scroll.
7. Главная проверка: модель должна совпадать с official-справочником.
8. Цвет, комплект, набор и комплектация не блокируют товар, а создают варианты.
9. Одинаковые варианты схлопываются, самая низкая цена выигрывает.
10. Цена Kaspi = source_price + 30%.
11. ETA Ozon/WB переносится в Kaspi без дополнительного buffer.
12. Если товар был в Kaspi, но сейчас market variant не найден, его надо снять с продажи, а не удалять.
13. Если seed-ссылка упала, проект пишет отчёт и Telegram-уведомление; руками проверяется источник.

## Решение по товарам

```text
market variant есть, в Kaspi нет -> create_candidate
market variant есть, в Kaspi есть -> update_candidate
Kaspi товар есть, market variant сейчас не найден -> pause_candidate
модель не подтверждена -> rejected / review_needed
```

## Текущая безопасность

Live-send в Kaspi отключён. Проект готовит только draft outputs:

```text
kaspi_create_api_payload.json
kaspi_price_stock.xml
kaspi_export_preview.csv/txt
kaspi_delivery_summary.json
```

## Важное уточнение v6.1

Папка `input/` убрана из активной архитектуры.

```text
скрипт скачивает official -> artifacts/raw/official/
скрипт парсит Ozon/WB listing -> artifacts/market_discovery/
скрипт строит состояние -> artifacts/state/
скрипт строит preview/exports -> artifacts/preview и artifacts/exports
```

Ручное заполнение Ozon/WB CSV не используется. Существующие товары Kaspi позже должны подтягиваться отдельным API/state-sync слоем, а не ручной папкой `input/`.
