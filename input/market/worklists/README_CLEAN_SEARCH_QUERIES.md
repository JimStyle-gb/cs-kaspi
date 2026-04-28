# Patch 24: clean market search queries

Этот патч укорачивает `search_query` в market worklists.

Что изменилось:

- раньше search_query мог включать длинный SEO-title и давать огромные Ozon/WB/Kaspi/Google ссылки;
- теперь search_query строится компактно:
  - бренд;
  - артикул / product_id;
  - model_key;
  - тип товара;
  - цвет / вариант;
  - короткая подсказка из названия только для аксессуаров.

Пример:

Было:
DEMIAND DK-2100/Черный-Wifi duos Аэрогриль с двумя чашами DEMIAND DUOS c Wifi управлением, с горячим обдувом воздуха ...

Стало:
DEMIAND DK-2100 Черный-Wifi DUOS аэрогриль черный

После установки запустить `Build_All` и проверить:
- `market_worklists/market_priority_missing_products.csv`;
- `market_worklists/market_worklist_summary.json`;
- поле `max_search_query_length` должно быть не больше 120.
