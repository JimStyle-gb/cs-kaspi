# input/market/worklists

Сюда кладутся заполненные market worklists.

## Как заполнять

Бери файл из artifacts:

```text
artifacts/market_worklists/market_priority_missing_products.csv
```

Заполняй только:

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

## Источники

```text
fill_source = ozon | wb | manual
```

Нельзя:

```text
fill_source = google
fill_source = kaspi
```

Google/Kaspi в HTML — только кнопки проверки, они не активируют товар.

## Проверка совпадения

Перед заполнением цены сверяй:

```text
артикул
модель
цвет
объём / комплектацию / размер
Wi‑Fi или отсутствие Wi‑Fi
```

Если цвет или важная характеристика отличается, это другой товар.
