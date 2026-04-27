# Реальный manual market input

Файл `demiand_manual_market_real.csv` содержит 3 контрольные строки для проверки боевого пути market-layer.

Назначение:
- проверить, что не все 85 товаров активируются сразу;
- активными должны стать только 3 товара из файла;
- остальные 82 товара должны остаться `wait_market_data`;
- exports должны показать 3 `create_candidates` при пустом Kaspi existing input.

Правила:
- `product_key` не менять;
- `price` — число без пробелов и валюты;
- `available` — `true` или `false`;
- `stock` — число;
- `lead_time_days` — срок в днях;
- `url` обязателен для настоящего источника цены/наличия.

Ожидаемый результат после `Build_All`:
- `market records: 3`;
- `matched market records: 3`;
- `ready_for_kaspi: 3`;
- `create_candidates: 3`;
- `skipped: 82`;
- `critical_count: 0`.
