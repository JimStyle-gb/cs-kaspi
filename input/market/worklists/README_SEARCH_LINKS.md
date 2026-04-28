CS-Kaspi market worklists with search links

После patch 23 в artifacts/market_worklists появятся дополнительные поля:
- search_ozon_url
- search_wb_url
- search_kaspi_url
- search_google_url
- market_priority_bucket

Главный файл для работы:
- artifacts/market_worklists/market_priority_missing_products.csv

Как пользоваться:
1. Открыть market_priority_missing_products.csv.
2. Сначала пройти товары с bucket 1_main_air_fryers и 2_main_kitchen.
3. Открывать search_* ссылки и искать реальную цену/наличие.
4. Заполнять только fill_source, fill_url, fill_price, fill_available, fill_stock, fill_lead_time_days.
5. product_key не менять.
6. Заполненный CSV класть в input/market/worklists/.
