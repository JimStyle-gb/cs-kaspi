# PROJECT CARD — CS-Kaspi v3 clean

## Назначение

CS-Kaspi — GitHub-only проект для построения своих уникальных Kaspi-карточек VAITAN.

## Главная логика

```text
Official supplier = техническая истина
Ozon/WB = рыночный слой цены и наличия
Kaspi = наш финальный слой VAITAN
```

## Текущее состояние v3

Сделана чистая база без тестовых активных файлов:

- Demiand official-layer;
- master_catalog;
- market input engine;
- market worklists;
- market safety gate;
- kaspi match layer;
- preview;
- draft exports;
- check report.

Удалено/не оставлено как активное:

- `supplier_2`;
- `__pycache__`;
- `*.pyc`;
- тестовые Kaspi existing записи;
- тестовые worklist строки;
- лишние patch README;
- активные временные market-строки.

## Что важно

1. VAITAN используется в Kaspi-title для создания своих карточек.
2. Ozon/WB используются для цены/наличия.
3. Google/Kaspi в worklists — только вспомогательные ссылки.
4. Google/Kaspi не могут активировать товар и не могут задавать цену.
5. Если у похожего товара отличается цвет/объём/Wi‑Fi/комплектация/артикул — это другой товар.
6. Все реальные market-строки должны проходить safety gate.

## Главный workflow

```text
Build_All
```

## Следующий практический этап

Заполнить реальные market-данные по приоритетным товарам из:

```text
artifacts/market_worklists/market_priority_missing_products.html
artifacts/market_worklists/market_priority_missing_products.csv
```

Заполненные CSV класть в:

```text
input/market/worklists/
```

После `Build_All` проверять:

```text
market_worklist_import_report
market_input_validation
master_catalog_summary
kaspi_export_summary
```

## До Kaspi API ещё не дошли

Текущий export-layer работает только как `draft_only`. Реальную отправку в Kaspi API добавлять позже через dry-run и ручное подтверждение.
