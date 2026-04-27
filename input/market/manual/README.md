# Manual market input

Файл `demiand_manual_market.csv` — первый ручной рыночный input для проверки полного пути CS-Kaspi:

```text
market input → market_state → master_catalog → kaspi_policy → preview
```

Важно:

- `product_key` не менять.
- `price` сейчас заполнен текущей ценой с official Demiand как временный тестовый market-input.
- Это не финальный Ozon/WB слой. После подключения Ozon/WB эти данные можно заменить или дополнить.
- `available=true`, `stock=3`, `lead_time_days=20` выставлены для проверки, что товары переходят в `ready_for_create_or_update`.
