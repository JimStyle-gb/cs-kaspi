# Demiand priority market fill batch 01

Файл:

```text
input/market/worklists/demiand_priority_market_fill_batch_01.csv
```

Это безопасный blank-batch на 27 приоритетных товаров Demiand.

## Как заполнять

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

## Проверка товара

Перед тем как ставить `match_*_ok = true`, сверяй:

```text
артикул
модель
цвет
объём
Wi‑Fi
количество чаш
комплектацию
размер/назначение аксессуара
```

Если отличается цвет или другая важная характеристика — это отдельный товар.
