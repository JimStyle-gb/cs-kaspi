# PATCH 29 — control fill for priority market batch 01

Этот файл оставляет batch из 27 приоритетных товаров, но заполняет market-поля только для 2 товаров:

- demiand_air_fryer_duos_wifi_black
- demiand_air_fryer_duos_wifi_white

Назначение патча: проверить, что после patch 28 частично заполненный batch работает правильно:

- заполненные fill_* строки импортируются;
- пустые строки остаются безопасными;
- Build_All не падает;
- ready_for_kaspi увеличивается только на 2 товара.

Заполнены только поля:

- fill_source
- fill_url
- fill_price
- fill_available
- fill_stock
- fill_lead_time_days

product_key менять нельзя.

Ожидаемый результат после Build_All:

- source_rows: 27
- blank_rows: 25
- filled_rows: 2
- imported_rows: 2
- invalid_rows: 0
- market records: 5
- ready_for_kaspi: 5
- create_candidates: 5
- skipped: 80
- critical_count: 0

Важно: это контрольный тест batch-importer. Перед боевой работой эти строки можно заменить на реальные Ozon/WB/manual данные.
