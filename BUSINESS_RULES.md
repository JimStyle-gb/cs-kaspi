# Business rules: CS-Kaspi v6.1

## Official

- Official source = техническая истина и SEO-база.
- Official source не решает, продаём ли товар сейчас.
- Official source используется для сильных Kaspi-карточек: описание, характеристики, фото, бренд, модель.

## Market

- Ozon/WB seed listings = реальные предложения для перепродажи.
- Используются только seed-ссылки из `config/market_sources.yml`.
- Запасной автоматический поиск запрещён.
- Product pages Ozon/WB по умолчанию не открываются.
- Если listing не открылся, карточек 0 или карточек меньше `expected_min_cards`, проблема идёт в отчёты и Telegram.

## Variant grouping

Один Kaspi candidate = один уникальный sellable variant.

Variant отличается, если отличается:

```text
модель
цвет
комплектация
набор / аксессуары
объём
Wi-Fi / без Wi-Fi
количество чаш
ключевая модификация
```

Если отличается только продавец или цена, это не новый товар. Берём самую низкую цену.

## Pricing

```text
kaspi_price = lowest_source_price + 30%
```

Без дополнительной скрытой маржи, кроме правил округления из `config/kaspi.yml`.

## Lead time

```text
Ozon/WB ETA -> Kaspi lead/preOrder без safety buffer
```

Если Ozon/WB показывает 5 мая, проект передаёт 5 мая / соответствующий срок без +1/+2 дней.

## Kaspi

- VAITAN должен быть в title.
- Реальный бренд сохраняется.
- Карточки должны быть уникальными, честными и несливаемыми.
- При отсутствии market variant товар снимается с продажи, но не удаляется.
- Live-send включать только отдельным будущим патчем после approval, mapping и allowlist.

## Input policy

- Ручной market input не используется.
- Ozon/WB данные собираются только скриптом из seed-ссылок `config/market_sources.yml`.
- Official raw pages и market discovery результаты сохраняются только в `artifacts/`.
- Существующие товары Kaspi позже должны приходить из API/state-sync, а не из ручной папки.
