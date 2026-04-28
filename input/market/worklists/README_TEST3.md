# CS-Kaspi — как подготовить market-данные для теста 3 товаров

Для первого реального теста не нужно активировать много товаров. Достаточно подготовить 3 сценария:

```text
create_candidate -> товар есть на Ozon/WB/manual, но его нет в Kaspi existing
update_candidate -> товар есть на Ozon/WB/manual и уже есть в Kaspi existing
pause_candidate  -> товар уже есть в Kaspi existing, но сейчас нет sellable market-data
```

## Для create_candidate

Заполни одну строку в `demiand_priority_market_fill_batch_01.csv`:

```text
fill_source
fill_url
fill_price
fill_available
fill_stock
fill_lead_time_days
match_article_ok
match_model_ok
match_color_ok
match_specs_ok
match_comment
```

И не добавляй этот `product_key` в `input/kaspi/existing/`.

## Для update_candidate

Заполни market-строку по товару и добавь этот же `product_key` в `input/kaspi/existing/` с реальным `kaspi_sku`.

## Для pause_candidate

Добавь `product_key` в `input/kaspi/existing/`, но не заполняй по нему sellable market-данные.

После `Build_All` смотри:

```text
artifacts/exports/kaspi_test3_plan.json
artifacts/exports/kaspi_test3_preview.txt
```

Эти файлы покажут, готов ли набор из 3 товаров для ручной проверки. Они ничего не отправляют в Kaspi.
