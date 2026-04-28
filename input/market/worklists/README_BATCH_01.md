# CS-Kaspi — Demiand priority market fill batch 01

Этот патч добавляет рабочий CSV для заполнения реальных market-данных по 27 приоритетным товарам Demiand.

Файл для заполнения:

`input/market/worklists/demiand_priority_market_fill_batch_01.csv`

HTML-помощник со ссылками:

`input/market/worklists/demiand_priority_market_fill_batch_01.html`

## Важно

Пока поля `fill_*` пустые, файл безопасен:
- товары не активируются;
- importer увидит строки, но не импортирует их как market-данные;
- `ready_for_kaspi` не должен увеличиться.

## Как заполнять

Для найденного товара заполняй только эти поля:

- `fill_source` — `ozon`, `wb` или `manual`
- `fill_url` — ссылка на товар / источник цены
- `fill_price` — цена закупа/рынка числом
- `fill_available` — `true` или `false`
- `fill_stock` — доступный остаток числом
- `fill_lead_time_days` — срок, обычно `20`

`product_key` менять нельзя.

## Что будет после заполнения

После запуска `Build_All` importer создаст:

`input/market/manual/_generated_from_worklists.csv`

И товары с заполненными `fill_*` перейдут в:

- `ready_for_kaspi`
- `kaspi_create_candidates` / `kaspi_update_candidates`

Пустые строки будут проигнорированы.
