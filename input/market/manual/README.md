# input/market/manual

Ручной market input для проверенных вручную строк.

Основной рабочий файл:

```text
input/market/manual/demiand_manual_market.csv
```

В чистой версии файл оставлен header-only. Заполняй его только реальными проверенными market-данными.

Обязательные поля активной строки:

```text
source = ozon | wb | manual
product_key
url
price
available
stock
lead_time_days
```

Google/Kaspi не являются источником цены и не должны попадать в `source`.
