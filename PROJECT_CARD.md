# Карточка проекта CS-Kaspi v2

## Текущая точка

Demiand official-layer уже доказал работоспособность: 5 категорий, 6 страниц каталога, 85 товаров, 85 product pages, 85 parsed, 85 normalized, 0 ошибок.

Главная проблема старого проекта была не в Demiand parser, а в том, что `Build_Master_Catalog` запускался отдельным workflow и не видел artifacts от `Refresh_Official_Sources`. Поэтому собирался пустой master catalog.

## Что изменено в v2

- Добавлен единый workflow `Build_All`.
- Удалены заглушки `supplier_2`, export/match/market stubs.
- Добавлен fail-fast для master catalog.
- Product keys приводятся к ASCII.
- Фото чистятся от `#`, lazy/svg/data-url, дублей; Kaspi images ограничиваются 10.
- Preview показывает все ключевые поля, включая цену, наличие, статус, title, attributes, description.
- Check report показывает реальные проблемы до перехода к market/export.

## Следующий этап после проверки v2

1. Запустить `Build_All`.
2. Проверить, что в `master_catalog.json` 85 товаров.
3. Проверить preview.
4. Только потом добавлять market layer Ozon/WB.
