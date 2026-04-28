# CS-Kaspi business rules

## Цель

Создавать свои уникальные карточки Kaspi под VAITAN, а не прикрепляться к чужим карточкам.

## Источники

| Источник | Роль | Может активировать товар | Может задавать цену |
|---|---|---:|---:|
| Official supplier | Техническая истина | Нет | Нет |
| Ozon | Цена/наличие/присутствие | Да | Да |
| WB | Цена/наличие/присутствие | Да | Да |
| Manual | Проверенный вручную market input | Да | Да |
| Google | Поиск/проверка | Нет | Нет |
| Kaspi search | Проверка похожих карточек/конкурентов | Нет | Нет |

## Правило цены

Временное правило v3:

```text
kaspi_price = lowest_sellable_market_price + 30%
```

Дополнительно применяется `min_margin_kzt` и округление из `config/kaspi.yml`.

## Правило уникального названия

Kaspi-title должен начинаться с VAITAN и сохранять реальный бренд:

```text
VAITAN Demiand ...
```

## Правило одинаковости товара

Одинаковое название на Ozon/WB не доказывает, что товар тот же. Обязательно сверять:

```text
артикул
модель
цвет
объём
Wi‑Fi / не Wi‑Fi
количество чаш
комплектацию
размер аксессуара
назначение аксессуара
```

Если отличается цвет или другой важный признак — это отдельный товар/вариант.

## Правило worklist

Заполненная строка worklist должна иметь:

```text
fill_source = ozon | wb | manual
fill_url
fill_price
fill_available
fill_stock
fill_lead_time_days
match_article_ok = true
match_model_ok = true
match_color_ok = true
match_specs_ok = true
```

Google/Kaspi в `fill_source` запрещены.
