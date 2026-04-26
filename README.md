# CS-Kaspi

Стартовый GitHub-only skeleton проекта под мульти-поставщицкую систему Kaspi.

## Базовая логика
official supplier data -> normalized catalog -> market layer (Ozon/WB only for price/availability) -> kaspi policy -> exports

## Точки входа
- python -m scripts.cs_kaspi.commands.refresh_official_sources
- python -m scripts.cs_kaspi.commands.build_master_catalog
- python -m scripts.cs_kaspi.commands.refresh_market_data
- python -m scripts.cs_kaspi.commands.build_preview
- python -m scripts.cs_kaspi.commands.match_kaspi
- python -m scripts.cs_kaspi.commands.export_updates
- python -m scripts.cs_kaspi.commands.export_creates
- python -m scripts.cs_kaspi.commands.export_pauses
- python -m scripts.cs_kaspi.commands.check_project


## Demiand starter

Этот skeleton уже содержит первый наполненный supplier-adapter `demiand`:
- categories fetch
- paginated catalog fetch
- product index build
- product pages fetch
- official product parse
- first official normalization

Первые state-файлы поставщика:
- `artifacts/state/demiand_product_index.json`
- `artifacts/state/demiand_official_products.json`
- `artifacts/state/official_state.json`

Запуск первого official pipeline:

```bash
python -m scripts.cs_kaspi.commands.refresh_official_sources
```
