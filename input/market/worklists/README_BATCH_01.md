# Demiand priority market fill batch 01

Файл:

```text
input/market/worklists/demiand_priority_market_fill_batch_01.csv
```

Это безопасный blank-batch на **29 приоритетных товаров Demiand**:

```text
20 аэрогрилей
6 кофеварок
2 блендера
1 печь
```

Аксессуары пока не входят в этот приоритетный batch.

## Где смотреть удобный HTML

HTML не должен лежать в `input/market/worklists/`.

Правильный HTML проект сам создаёт после `Build_All` здесь:

```text
artifacts/market_worklists/market_priority_missing_products.html
```

В `input/market/worklists/` должен лежать только CSV для ручного заполнения.

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

`product_key` и служебные поля не менять.

## Источники

Разрешено:

```text
fill_source = ozon | wb | manual
```

Нельзя:

```text
fill_source = google
fill_source = kaspi
```

Google и Kaspi в HTML — только кнопки для ручной проверки, они не активируют товар и не задают цену.

## Проверка товара

Перед тем как ставить `match_*_ok = true`, сверяй:

```text
артикул
модель
цвет
объём
Wi-Fi / без Wi-Fi
количество чаш
комплектацию
размер/назначение аксессуара
```

Если отличается цвет или другая важная характеристика — это отдельный товар, такую строку не активировать.
