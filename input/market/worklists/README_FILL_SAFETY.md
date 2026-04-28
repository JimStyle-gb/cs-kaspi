# CS-Kaspi: безопасное заполнение market worklists

Этот патч усиливает проверку файлов в `input/market/worklists/`.

## Что теперь считается безопасным

Пустые строки из worklist разрешены. Например, если в batch-файле есть `product_key`, `official_title`, `search_ozon_url`, но поля `fill_*` пустые — такая строка просто считается `blank` и не активирует товар.

## Что считается активной строкой

Строка становится активной, если заполнено хотя бы одно из полей:

- `fill_source`
- `fill_url`
- `fill_price`
- `fill_available`
- `fill_stock`
- `fill_lead_time_days`
- `rating`
- `reviews_count`

## Для sellable-строки нужно заполнить

- `fill_url`
- `fill_price`
- `fill_stock`
- `fill_available` желательно `true`
- `fill_lead_time_days` можно оставить пустым — тогда будет 20

Если строка заполнена частично, `Build_All` должен упасть с понятной ошибкой в:

```text
artifacts/reports/market_worklist_import_report.txt
```

## Зачем это нужно

Чтобы случайно не включить товар в market-layer по наполовину заполненной строке.
