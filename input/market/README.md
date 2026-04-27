# CS-Kaspi market input

Этот слой нужен только для рыночных данных: цена, наличие, остаток, срок и факт присутствия на Ozon/WB/другом источнике.
Технические характеристики товара берутся из official supplier layer, а не из marketplace.

Поддерживаемые файлы внутри `input/market/`:

- `.json`
- `.yml`
- `.yaml`
- `.csv`

Файлы можно класть, например, так:

- `input/market/ozon/products.json`
- `input/market/wb/products.csv`
- `input/market/manual/products.yml`

Минимальные поля записи:

```json
{
  "product_key": "demiand_air_fryer_sanders_max_wifi_white",
  "source": "ozon",
  "title": "Название на маркетплейсе",
  "url": "https://...",
  "price": 89900,
  "available": true,
  "stock": 1,
  "lead_time_days": 3
}
```

Матчинг выполняется по очереди:

1. `product_key`
2. `supplier_key` + `official_article`
3. `official_article`
4. `supplier_key` + `model_key` + `variant_key`
5. `model_key` + `variant_key`
6. `title`

Файлы с `example`, `sample`, `readme` в названии игнорируются загрузчиком, чтобы примеры случайно не попали в рабочий расчёт.
