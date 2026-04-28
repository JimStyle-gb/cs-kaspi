# input/market/worklists

Сюда можно положить заполненный CSV из `artifacts/market_worklists/market_missing_products.csv`.

Зачем это нужно:
- не переносить строки вручную в `input/market/manual`;
- не ошибаться с колонками;
- `Build_All` сам конвертирует заполненные `fill_*` поля в стандартный market input.

Как пользоваться:
1. Возьми файл `artifacts/market_worklists/market_missing_products.csv`.
2. Заполни только нужные строки в колонках:
   - `fill_source`
   - `fill_url`
   - `fill_price`
   - `fill_available`
   - `fill_stock`
   - `fill_lead_time_days`
3. Сохрани файл сюда, например:
   `input/market/worklists/demiand_filled_market_worklist.csv`
4. Запусти `Build_All`.

Важно:
- `product_key` нельзя менять.
- Пустые строки будут проигнорированы.
- Если `fill_source` пустой, система поставит `manual`.
- Если `fill_available` пустой, но `fill_stock` больше 0, система поставит `available=true`.
- Конвертированный файл создаётся временно во время workflow:
  `input/market/manual/_generated_from_worklists.csv`.
