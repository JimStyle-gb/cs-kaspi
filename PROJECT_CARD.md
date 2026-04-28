# PROJECT CARD — CS-Kaspi v4 fresh

## Текущая точка

Проект пересобран как чистая v4-структура без patch-мусора и без лишних тестовых данных.

Сохранена рабочая логика v3/v4:

```text
official -> master -> market -> kaspi_match -> kaspi_policy -> preview -> exports -> delivery draft -> test3 plan
```

## Подтверждённые правила

```text
Official = техническая истина.
Ozon/WB/manual = market-layer.
Kaspi = финальный VAITAN export-layer.
Google/Kaspi search = только ручная проверка.
VAITAN обязателен в Kaspi title.
Новые товары без market-data не создаём.
Существующие Kaspi товары без market-data снимаем с продажи, но не удаляем.
HTML worklists генерируются только в artifacts.
input/worklists содержит только CSV для заполнения.
Live-send пока отсутствует намеренно.
```

## Demiand official-layer

Ожидаемое рабочее состояние после Build_All:

```text
official products: 85
master catalog: 85
market records: 0 до заполнения реальных market-данных
ready_for_kaspi: 0 до заполнения реальных market-данных
skipped: 85
critical_count: 0
```

Категории Demiand:

```text
air_fryers: 20
coffee_makers: 6
blenders: 2
ovens: 1
air_fryer_accessories: 56
```

## Следующий практический этап

Заполнить реальные market-данные сначала по 3 товарам:

```text
1 товар для create_candidate
1 товар для update_candidate
1 товар для pause_candidate
```

Для этого нужны:

```text
real Ozon/WB/manual market rows
real Kaspi existing rows для update/pause
проверка preview
проверка kaspi_test3_plan
```

Только после этого добавлять live-send отдельным защищённым патчем.
