# CS-Kaspi v4 fresh

CS-Kaspi — GitHub-only проект для подготовки товаров к продаже на Kaspi под торговым слоем VAITAN.

Главная цель проекта: создавать и поддерживать свои уникальные Kaspi-карточки, а не прикрепляться к чужим карточкам конкурентов.

## Главная логика

```text
official supplier source -> master catalog -> market layer -> Kaspi match -> Kaspi policy -> preview -> draft exports -> delivery draft -> controlled test plan
```

## Источники данных

```text
Official-source = техническая истина по товару.
Ozon/WB/manual = market-layer для цены, наличия, ссылки, stock и lead time.
Kaspi existing = наши уже существующие товары для update/pause.
Google/Kaspi search = только ручная проверка, не источник цены.
```

От official-source берём: бренд, модель, артикул, категорию, название, описание, характеристики, фото, цвет, комплектацию и официальную ссылку.

От Ozon/WB берём только рыночные поля: найден ли товар, цена, наличие, stock, ссылка, lead_time_days.

## Правило VAITAN

Каждый Kaspi-ready title должен содержать VAITAN и при этом сохранять реальный бренд товара.

Пример:

```text
VAITAN аэрогриль Demiand DUOS DK-2100 черный с двумя чашами
```

Проект не должен копировать название Ozon/WB или official-source один в один.

## Когда товар готов к Kaspi

Товар можно готовить к Kaspi только если:

```text
1. товар есть в official-source;
2. товар найден в Ozon/WB/manual как market-source;
3. совпадение подтверждено по модели/артикулу/цвету/ключевым характеристикам;
4. есть цена, stock и lead time;
5. Kaspi policy смогла собрать title, description, attributes, images и цену.
```

Если market-source нет, новый товар не создаём. Если товар уже был у нас в Kaspi, но сейчас нет market-source, готовим pause_candidate, но карточку не удаляем.

## Каналы Kaspi

В v4 заложена гибридная схема:

```text
API draft payload -> для будущего создания новых карточек.
XML price/stock draft -> для будущего обновления цены, остатков, preOrder и снятия с продажи.
Excel/manual -> только запасной ручной вариант, не основной канал проекта.
```

Сейчас live-send отсутствует специально. Все Kaspi delivery-файлы создаются только в draft_only режиме.

## Основной workflow

Workflow: `.github/workflows/build_all.yml`

Расписание: ежедневно в 02:00 по Алматы.

Цепочка Build_All:

```text
1. refresh_official_sources
2. import_market_worklists
3. refresh_market_data
4. validate_market_inputs
5. refresh_kaspi_matches
6. build_master_catalog
7. build_market_template
8. build_market_worklist
9. build_kaspi_match_template
10. build_preview
11. build_kaspi_exports
12. build_kaspi_delivery
13. build_kaspi_test3_plan
14. check_project
```

## Ключевые артефакты

```text
artifacts/state/master_catalog.json
artifacts/state/master_catalog_summary.json
artifacts/preview/kaspi_preview.json
artifacts/preview/kaspi_preview.txt
artifacts/preview/kaspi_preview.xml
artifacts/exports/kaspi_create_candidates.json
artifacts/exports/kaspi_update_candidates.json
artifacts/exports/kaspi_pause_candidates.json
artifacts/exports/kaspi_create_api_payload.json
artifacts/exports/kaspi_price_stock.xml
artifacts/exports/kaspi_delivery_summary.json
artifacts/exports/kaspi_test3_plan.json
artifacts/exports/kaspi_test3_preview.txt
artifacts/reports/check_project_report.txt
```

## Market worklists

HTML worklists проект генерирует сам в:

```text
artifacts/market_worklists/
```

В `input/market/worklists/` должны лежать только CSV-файлы для заполнения. Статичные HTML-файлы туда не кладём.

Главный batch сейчас:

```text
input/market/worklists/demiand_priority_market_fill_batch_01.csv
```

В нём 29 приоритетных товаров Demiand:

```text
20 аэрогрилей
6 кофеварок
2 блендера
1 печь
```

Аксессуары идут позже.

## Безопасность live-теста

Первый реальный тест Kaspi должен быть только на 3 товара:

```text
1 товар -> create_candidate
1 товар -> update_candidate
1 товар -> pause_candidate
```

Перед live-send обязательно:

```text
KASPI_LIVE_SEND=false по умолчанию
KASPI_MAX_ACTIONS=3
KASPI_ALLOWED_SKUS=только 3 проверенных SKU
KASPI_DRY_RUN=true до финального разрешения
Kaspi category/attribute mapping подтверждён
XML company/merchant/store заполнены реальными значениями
```

В этой версии live-send не реализован. Это сделано намеренно, чтобы проект не мог случайно отправить товары в Kaspi.

## Локальный запуск

```bash
pip install -r requirements.txt
python -m scripts.cs_kaspi.commands.build_all
```

Проверка синтаксиса:

```bash
python -m compileall scripts
```
