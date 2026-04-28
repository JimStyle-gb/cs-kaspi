# CS-Kaspi v3 clean

Чистая безопасная база проекта **CS-Kaspi**.

Главная цель проекта: создавать и обновлять **свои уникальные Kaspi-карточки VAITAN**, а не прикрепляться к чужим карточкам.

## Главная схема

```text
official supplier source
        ↓
official_state
        ↓
market input: Ozon/WB/manual
        ↓
market_state
        ↓
kaspi_match
        ↓
master_catalog
        ↓
kaspi_policy
        ↓
preview/check
        ↓
draft exports
        ↓
kaspi delivery draft
```

## Роли источников

```text
Official source = техническая истина: модель, артикул, характеристики, фото, описание.
Ozon/WB = рыночная проверка: наличие, цена, ссылка, факт присутствия.
Google = только вспомогательный поиск, не источник цены.
Kaspi search = только проверка похожих карточек/конкурентов, не источник закупочной цены.
Kaspi export = наш финальный слой VAITAN.
```

## Важные бизнес-правила

1. **VAITAN обязательно участвует в Kaspi-title**, если это не сломает модерацию.
2. Реальный бренд товара сохраняется: например `VAITAN Demiand ...`.
3. Цена Kaspi строится не копированием, а через `config/kaspi.yml -> price_policy`.
4. В v3 временная наценка: **30%** + минимальная маржа из конфига.
5. Google/Kaspi не могут активировать товар и не могут задавать цену.
6. Если товар на Ozon/WB похож, но отличается цветом, объёмом, Wi‑Fi, чашами, комплектацией, размером или артикулом — это другой товар.
7. Для заполненных worklist-строк нужно подтверждать совпадение:
   - `match_article_ok`
   - `match_model_ok`
   - `match_color_ok`
   - `match_specs_ok`

## Главный запуск

В GitHub Actions запускай только:

```text
Build_All
```

Он делает весь безопасный цикл в одном job:

```text
1. refresh official sources
2. import filled market worklists
3. refresh market data
4. validate market inputs
5. refresh kaspi matches
6. build master catalog
7. build market templates/worklists
8. build preview
9. build draft exports
10. build Kaspi delivery draft
11. check project
```

## Что сейчас внутри

- Первый поставщик: `Demiand`.
- Архитектура мульти-поставщицкая и мультикатегорийная.
- Тестовые `KSP-TEST`, `KSP-UPDATE`, `KSP-PAUSE` файлы удалены.
- Тестовые market-строки удалены.
- Боевые market-файлы лежат как header-only, пока ты сам не заполнишь реальные данные.

## Как работать с market-данными

После `Build_All` скачай artifacts:

```text
artifacts/market_worklists/market_priority_missing_products.html
artifacts/market_worklists/market_priority_missing_products.csv
```

В HTML открывай кнопки:

```text
Ozon / WB / Kaspi / Google / Official
```

Важно:

```text
Ozon/WB — для цены и наличия.
Kaspi/Google — только проверить похожие карточки и совпадения.
```

Заполняй в CSV только:

```text
fill_source
fill_url
fill_price
fill_available
fill_stock
fill_lead_time_days
match_article_ok
match_model_ok
match_color_ok
match_specs_ok
match_comment
```

Потом клади заполненный CSV в:

```text
input/market/worklists/
```

`Build_All` сам импортирует заполненные строки в market-layer.

## Как добавлять нового поставщика

Для нового поставщика добавляется отдельный supplier package:

```text
config/suppliers/<supplier_key>.yml
scripts/cs_kaspi/suppliers/<supplier_key>/
```

Supplier-layer должен выдать unified official state:

```text
artifacts/state/<supplier_key>_official_products.json
```

Core/catalog/kaspi_policy не должны содержать supplier-specific костыли.

## Безопасность

Сейчас проект ничего не отправляет в Kaspi API. Он создаёт только draft exports:

```text
artifacts/exports/kaspi_create_candidates.json
artifacts/exports/kaspi_update_candidates.json
artifacts/exports/kaspi_pause_candidates.json
artifacts/exports/kaspi_export_preview.csv
artifacts/exports/kaspi_create_api_payload.json
artifacts/exports/kaspi_price_stock.xml
artifacts/exports/kaspi_delivery_summary.json
artifacts/exports/kaspi_delivery_preview.txt
```

Реальный API-слой надо добавлять позже через `dry_run` и ручное подтверждение.

## Kaspi delivery draft

`Build_All` дополнительно готовит будущий слой доставки в Kaspi, но всё ещё в безопасном режиме `draft_only`:

```text
artifacts/exports/kaspi_create_api_payload.json
artifacts/exports/kaspi_price_stock.xml
artifacts/exports/kaspi_update_plan.json
artifacts/exports/kaspi_pause_plan.json
artifacts/exports/kaspi_delivery_summary.json
artifacts/exports/kaspi_delivery_preview.txt
```

Логика:

```text
create_candidate -> draft JSON payload для будущего API-create
update_candidate -> draft XML для цены/остатка/срока
pause_candidate  -> draft XML available=no / stockCount=0
```

В этих файлах ничего не отправляется в Kaspi. XML пока содержит `DRAFT_COMPANY`, `DRAFT_MERCHANT_ID`, `DRAFT_STORE_ID`; перед live-режимом их нужно заменить конфигом и добавить защиту allowlist/max_actions/approve-file.

## Patch 33: контролируемый тест 3 товаров

После Kaspi delivery draft проект дополнительно строит безопасный план первого теста из 3 товаров:

```text
artifacts/exports/kaspi_test3_plan.json
artifacts/exports/kaspi_test3_preview.txt
```

Цель плана:

```text
1 товар -> create_candidate
1 товар -> update_candidate
1 товар -> pause_candidate
```

Этот слой ничего не отправляет в Kaspi. Он только проверяет, есть ли в draft exports нужные 3 сценария, какие SKU будут использованы и какие блокеры мешают live-тесту.

Важно:

```text
create_candidate появляется, когда есть подтверждённые market-данные и нет Kaspi existing match.
update_candidate появляется, когда есть подтверждённые market-данные и есть Kaspi existing match.
pause_candidate появляется, когда есть Kaspi existing match, но нет sellable market-данных.
```

Перед любым live-режимом обязательно должны быть:

```text
реальные Ozon/WB/manual market-данные;
реальные existing Kaspi SKU для update/pause;
маппинг категории и обязательных характеристик Kaspi для create;
allowlist только из 3 SKU;
лимит KASPI_MAX_ACTIONS=3;
dry-run preview перед отправкой.
```
