# Test filled market worklist

Тестовые строки importer-слоя отключены.

Файл `demiand_filled_worklist_test.csv` оставлен только с заголовком, чтобы пример структуры не потерялся, но товары больше не активируются.

Для реальной работы не заполняй этот test-файл. Создавай отдельный файл в этой же папке, например:

`input/market/worklists/demiand_filled_worklist_real_01.csv`

Правило:

- `product_key` не менять;
- `fill_source` = `manual`, `ozon` или `wb`;
- `fill_url` обязательно для активной строки;
- `fill_price` обязательно для активной строки;
- `fill_available` = `true` / `false`;
- `fill_stock` обязательно для активной строки;
- `fill_lead_time_days` желательно заполнять, если отличается от дефолта.
