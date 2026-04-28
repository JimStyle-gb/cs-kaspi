# PATCH 30 — отключение контрольного заполнения batch 01

Файл `demiand_priority_market_fill_batch_01.csv` сохранён как рабочий batch на 27 приоритетных товаров, но контрольные `fill_*` значения из patch 29 очищены.

Ожидаемое состояние после Build_All:

- `source_rows`: 27
- `blank_rows`: 27
- `filled_rows`: 0
- `imported_rows`: 0
- `ready_for_kaspi`: 3
- `create_candidates`: 3
- `skipped`: 82

Для боевой работы заполнять только поля:

- `fill_source`
- `fill_url`
- `fill_price`
- `fill_available`
- `fill_stock`
- `fill_lead_time_days`

`product_key` не менять.
