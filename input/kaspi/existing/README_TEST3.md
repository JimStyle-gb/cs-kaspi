# CS-Kaspi — подготовка теста 3 товаров

Этот каталог нужен только для реальных существующих товаров из твоего Kaspi-кабинета.

Для первого контролируемого теста нужны 3 сценария:

```text
1 товар -> create_candidate
1 товар -> update_candidate
1 товар -> pause_candidate
```

## Как получить update_candidate

1. Выбери товар, который уже есть у тебя в Kaspi.
2. Внеси его в `input/kaspi/existing/` обычным CSV/JSON/YML файлом.
3. В этой строке обязательно укажи `product_key` из CS-Kaspi и реальный `kaspi_sku`.
4. По этому же `product_key` заполни market-данные Ozon/WB/manual.

Тогда проект увидит:

```text
есть Kaspi match + есть market data = update_candidate
```

## Как получить pause_candidate

1. Выбери товар, который уже есть у тебя в Kaspi.
2. Внеси его в `input/kaspi/existing/` с реальным `product_key` и `kaspi_sku`.
3. По этому `product_key` НЕ заполняй sellable market-данные Ozon/WB/manual.

Тогда проект увидит:

```text
есть Kaspi match + нет market data = pause_candidate
```

## Минимальные поля CSV

```csv
product_key,kaspi_sku,kaspi_product_id,kaspi_title,kaspi_url,kaspi_price,kaspi_stock,kaspi_available
```

`kaspi_sku` должен быть реальным SKU из твоего Kaspi. Для update/pause проект не должен генерировать новый SKU.

Файл `kaspi_existing_test3_sample.csv` — только пример структуры. Он содержит слово `sample`, поэтому проект его игнорирует.
