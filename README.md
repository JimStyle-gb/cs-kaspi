# CS-Kaspi

Чистая рабочая основа проекта **CS-Kaspi**.

## Главная логика

```text
official supplier source -> official_state -> market_state -> master_catalog -> kaspi_policy -> preview/check -> позже export
```

Правила проекта:

1. **Официальный источник поставщика/бренда** — техническая истина по товару: название, модель, описание, характеристики, фото.
2. **Ozon/WB** — только рыночный слой: цена, наличие, факт присутствия/продаж. Не источник технической правды.
3. **Kaspi policy** — финальный слой, где строятся наши названия, цены, остатки, описания, атрибуты и статусы.
4. Проект сразу сделан **мульти-поставщицким** и **мультикатегорийным**. Demiand — первый подключённый supplier-adapter, а не центр архитектуры.
5. Supplier-specific логика живёт только в `scripts/cs_kaspi/suppliers/<supplier>/`.
6. Общий catalog/core/kaspi_policy не должен содержать `if supplier == demiand`.

## Куда вставить

Архив распаковать в корень репозитория `CS-Kaspi` с заменой старых файлов.
В архиве уже сохранены правильные пути:

```text
.github/workflows/...
config/...
scripts/cs_kaspi/...
requirements.txt
README.md
```

## Главный запуск

В GitHub Actions запускай:

```text
Build_All
```

Он делает всё в одном job, чтобы `Build_Master_Catalog` видел state-файлы, созданные предыдущими шагами:

```text
1. refresh official sources
2. refresh market data from input/market
3. build master catalog
4. build market input template
5. build preview
6. check project
7. upload artifacts
```

## Отдельные команды

```bash
python -m scripts.cs_kaspi.commands.refresh_official_sources
python -m scripts.cs_kaspi.commands.refresh_market_data
python -m scripts.cs_kaspi.commands.build_master_catalog
python -m scripts.cs_kaspi.commands.build_market_template
python -m scripts.cs_kaspi.commands.build_preview
python -m scripts.cs_kaspi.commands.check_project
python -m scripts.cs_kaspi.commands.build_all
```

Важно: отдельный `build_master_catalog` не собирает пустой master молча. Если official state отсутствует, он падает с понятной ошибкой.

## Рыночный слой market-layer v1

Market-layer v1 не парсит Ozon/WB live-страницы. Он читает подготовленные файлы из `input/market/` и использует их только как рыночный слой:

```text
цена -> наличие -> остаток -> срок -> sellable/not sellable
```

Технические характеристики и описание по-прежнему берутся из official supplier layer.

Поддерживаемые входные форматы:

```text
input/market/ozon/*.json|*.yml|*.yaml|*.csv
input/market/wb/*.json|*.yml|*.yaml|*.csv
input/market/manual/*.json|*.yml|*.yaml|*.csv
```

Если рыночных файлов нет, сборка не падает: товары остаются в статусе `catalog_only / wait_market_data`.

Если рыночная запись найдена и товар доступен, `kaspi_policy` строит цену через `config/kaspi.yml -> price_policy`, а не копирует цену маркетплейса напрямую.

## Шаблон первого market input

После `Build_All` автоматически создаётся папка:

```text
artifacts/market_templates/
```

В ней будут:

```text
manual_market_template.csv
manual_market_template.json
README.txt
```

Это безопасный шаблон на базе текущего `master_catalog.json`. Он нужен, чтобы сделать первый реальный market input без ошибок в `product_key`.

Рабочая схема:

```text
1. скачать artifacts/market_templates/manual_market_template.csv
2. заполнить price / available / stock / lead_time_days / url
3. положить готовый файл в input/market/manual/demiand_manual_market.csv
4. запустить Build_All
```

Колонки с `_` в начале — справочные. `product_key` менять нельзя.

## Выходные файлы

После `Build_All` должны появиться:

```text
artifacts/state/demiand_product_index.json
artifacts/state/demiand_official_products.json
artifacts/state/official_state.json
artifacts/state/market_state.json
artifacts/state/master_catalog.json
artifacts/state/master_catalog_summary.json
artifacts/market_templates/manual_market_template.csv
artifacts/market_templates/manual_market_template.json
artifacts/market_templates/README.txt
artifacts/preview/kaspi_preview.json
artifacts/preview/kaspi_preview.yml
artifacts/preview/kaspi_preview.xml
artifacts/preview/kaspi_preview.txt
artifacts/reports/market_report.txt
artifacts/reports/market_unmatched_records.json
artifacts/reports/check_project_report.json
artifacts/reports/check_project_report.txt
```

## Как добавлять нового поставщика потом

Для нового поставщика нужно добавить только:

```text
config/suppliers/<supplier_key>.yml
scripts/cs_kaspi/suppliers/<supplier_key>/build_supplier_state.py
```

`build_supplier_state.py` должен вернуть и записать:

```text
artifacts/state/<supplier_key>_official_products.json
```

Формат у всех поставщиков одинаковый:

```json
{
  "meta": {"supplier_key": "...", "products_count": 0},
  "products": []
}
```

Дальше общий master catalog подхватит его сам.
