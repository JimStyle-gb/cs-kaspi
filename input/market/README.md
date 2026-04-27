# CS-Kaspi market input

Эта папка предназначена только для рыночного слоя: цена, наличие, остаток, срок и ссылка-источник.
Технические характеристики, описание, фото и модель товара берутся из official-layer поставщика.

Поддерживаемые папки:

```text
input/market/ozon/
input/market/wb/
input/market/manual/
```

Поддерживаемые форматы:

```text
.csv
.json
.yml
.yaml
```

Обязательные поля для активной sellable-строки:

```text
product_key
source
price
available
stock
lead_time_days
url
```

Правила безопасности:

- `product_key` нельзя менять вручную — бери его из `artifacts/market_templates/manual_market_template.csv`.
- Для Ozon/WB активная строка без `url` считается критичной ошибкой.
- Для `manual` активная строка без `url` считается косметической ошибкой, но URL всё равно лучше заполнять.
- Пустой CSV только с заголовком разрешён и означает, что рыночные данные пока не подключены.
- Файлы с `example`, `sample`, `readme` в имени игнорируются.
- Тестовые временные цены не оставляй в рабочем проекте.

После добавления реального market input запускай:

```text
Build_All
```

Смотри отчёты:

```text
artifacts/reports/market_report.txt
artifacts/reports/market_input_validation.txt
artifacts/reports/check_project_report.txt
artifacts/exports/kaspi_export_preview.csv
```
