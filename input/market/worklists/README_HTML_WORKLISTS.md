# HTML worklists

Patch 25 добавляет HTML-страницы в `artifacts/market_worklists/`:

- `market_priority_missing_products.html` — приоритетный список товаров без market-данных с кликабельными ссылками Ozon/WB/Kaspi/Google/Official.
- `market_missing_products.html` — полный список товаров без market-данных.
- `market_ready_products.html` — товары, по которым market-данные уже есть.

HTML-файлы нужны только для удобного поиска. Боевые данные всё равно заполняются в CSV через `fill_*` колонки и кладутся в `input/market/worklists/`.

`product_key` менять нельзя.
