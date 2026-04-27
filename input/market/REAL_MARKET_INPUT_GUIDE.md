# CS-Kaspi: боевые market input файлы

Эти файлы нужны для реальных цен, наличия и сроков. Они не заменяют official-layer: характеристики, фото, описание и модель берутся из official source.

## Куда класть

- `input/market/ozon/demiand_ozon_market.csv` — Ozon-источник.
- `input/market/wb/demiand_wb_market.csv` — Wildberries-источник.
- `input/market/manual/demiand_manual_market_real.csv` — ручной безопасный источник.

## Главное правило

`product_key` менять нельзя. Его нужно брать из `artifacts/market_templates/manual_market_template.csv` или из `master_catalog.json`.

## Обязательные поля для активной строки

Для строки, где товар реально продаётся, должны быть заполнены:

- `source` — `ozon`, `wb` или `manual`;
- `product_key`;
- `url` — ссылка на источник цены/наличия;
- `price` — рыночная цена;
- `available` — `true`;
- `stock` — остаток/условный остаток;
- `lead_time_days` — срок передачи/доставки.

Если строки нет или она пустая — товар остаётся `wait_market_data` и не попадёт в create/update.

## Безопасность

`Build_All` запускает `validate_market_inputs.py`. Если активная строка без цены, остатка, availability или URL — сборка должна остановиться с critical-ошибкой.

## Что нельзя делать

- Нельзя загружать тестовые цены как боевые.
- Нельзя оставлять `url` пустым для Ozon/WB.
- Нельзя менять `product_key` вручную.
- Нельзя считать Ozon/WB технической истиной товара: это только market-layer.
