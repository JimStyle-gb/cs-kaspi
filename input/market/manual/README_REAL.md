# Реальный manual market input

`demiand_manual_market_real.csv` в v3 clean оставлен header-only.

Используй его только для проверенных вручную market-строк.

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
