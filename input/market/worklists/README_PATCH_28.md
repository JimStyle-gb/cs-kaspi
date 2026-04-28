# Patch 28 — fix blank generated worklists

Этот патч исправляет ошибку patch 27: строки из `demiand_priority_market_fill_batch_01.csv` считались заполненными из-за служебных колонок `recommended_source`, `lead_time_days`, `current_market_*` и search-ссылок.

Теперь для generated worklist активируют товар только реальные поля `fill_*`:

- `fill_source`
- `fill_url`
- `fill_price`
- `fill_available`
- `fill_stock`
- `fill_lead_time_days`

Пустые строки worklist снова разрешены. Частично заполненные `fill_*` строки по-прежнему будут падать с ошибкой, чтобы не включить товар случайно.
