# input/market

Папка для реальных market-данных.

## Разрешённые источники для цены и наличия

```text
ozon
wb
manual
```

## Запрещено как источник цены

```text
google
kaspi
```

Google и Kaspi используются только как ссылки в worklists для ручной проверки. Они не должны попадать в `fill_source`.

## Куда класть данные

```text
input/market/ozon/
input/market/wb/
input/market/manual/
input/market/worklists/
```

Самый безопасный путь — заполнять CSV из artifacts/worklists и класть его в:

```text
input/market/worklists/
```

Importer сам создаст:

```text
input/market/manual/_generated_from_worklists.csv
```

## Обязательные поля для активной sellable строки

```text
source / fill_source
product_key
url / fill_url
price / fill_price
available / fill_available
stock / fill_stock
lead_time_days / fill_lead_time_days
```

Для generated worklists дополнительно обязательны подтверждения:

```text
match_article_ok
match_model_ok
match_color_ok
match_specs_ok
```
