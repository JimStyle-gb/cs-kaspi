# BUSINESS RULES — CS-Kaspi v4

## 1. Official-source

Официальный сайт поставщика — главный источник технической информации.

Берём оттуда:

```text
brand
model
article
category
title
description
attributes
images
color
kit/complectation
official_url
```

Не подменяем technical truth данными Ozon/WB/Kaspi.

## 2. Market-layer

Ozon, WB и manual input используются только для рыночного подтверждения:

```text
market_source
market_url
market_price
market_available
market_stock
lead_time_days
```

Запрещено использовать Google/Kaspi как источник цены.

## 3. Правило совпадения товара

Товар считается найденным только если совпадает не просто название, а ключевые признаки:

```text
article/model
color
volume/size
Wi-Fi / без Wi-Fi
number of bowls
power
kit/complectation
accessory compatibility
photo similarity by human review when needed
```

Если совпадение сомнительное — товар остаётся skipped/wait_market_data.

## 4. Kaspi actions

```text
market есть + kaspi existing нет -> create_candidate
market есть + kaspi existing есть -> update_candidate
market нет + kaspi existing есть -> pause_candidate
market нет + kaspi existing нет -> skipped
```

Pause означает снять с продажи без удаления карточки.

## 5. VAITAN policy

Каждая новая карточка должна быть уникальной и защищать нас от лишнего прикрепления конкурентов.

Kaspi title должен содержать:

```text
VAITAN + тип товара + реальный бренд + модель/артикул + цвет/ключевая особенность
```

## 6. Цена

Финальная цена строится только от market-layer.

Текущая базовая политика:

```text
берём минимальную подходящую цену из ozon/wb/manual
прибавляем markup_percent из config/kaspi.yml
округляем по правилу config/kaspi.yml
```

Google/Kaspi не используются как price source.

## 7. Live safety

Live-send запрещён до отдельного этапа.

Первый live-тест должен быть строго:

```text
1 create
1 update
1 pause
max 3 actions
allowlist SKU обязателен
ручная проверка preview обязательна
```
