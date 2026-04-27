CS-Kaspi patch 09 — test Kaspi existing input

Этот файл нужен только для проверки Kaspi-match layer.

Ожидаемый результат после Build_All:
- kaspi_match_state.json: total_records = 3, matched_products = 3;
- kaspi_create_candidates.json: 82 товара;
- kaspi_update_candidates.json: 3 товара;
- kaspi_pause_candidates.json: 0 товаров.

Важно: это НЕ настоящая выгрузка из Kaspi. Перед боевым режимом этот файл нужно заменить реальной выгрузкой текущих товаров Kaspi.
