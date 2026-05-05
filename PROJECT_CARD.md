# Карточка проекта CS-Kaspi v7 WB-only

## Что это

CS-Kaspi — проект для автоматической подготовки VAITAN-карточек Kaspi.
Новая версия v7 работает только с WB как market-source.

## Роли слоёв

1. `official` — официальный сайт поставщика. Это технический справочник: модель, артикул, характеристики, описание, фото, SEO.
2. `market WB` — реальные продаваемые предложения: title, url, price, stock, ETA, цвет, комплект, набор.
3. `kaspi_policy` — финальный слой карточки: VAITAN title, price, stock, lead time, images, attributes, description.
4. `exports/delivery` — безопасные draft-файлы для проверки, без live-send.

## Главные правила

- Рабочий market-source только WB.
- Работают только WB seed-ссылки из `config/market_sources.yml`.
- Fallback-поиска нет.
- Product pages WB не открываются как основной поток.
- Одинаковые variants схлопываются.
- Lowest WB price внутри одинакового варианта выигрывает.
- Kaspi price = WB price + 30%, затем округление вниз до последних двух цифр `00`.
- ETA переносится без buffer.
- VAITAN обязателен в title.
- Live-send выключен.

## Цепочка Build_All

`refresh_official_sources` -> `discover_market_data` -> `refresh_market_data` -> `refresh_kaspi_matches` -> `build_master_catalog` -> `build_preview` -> `build_kaspi_exports` -> `build_kaspi_delivery` -> `check_project` -> `send_telegram_report`.

## Что делать дальше после v7

1. Прогнать `Build_All`.
2. Проверить WB counts в `seed_url_report.txt`.
3. Проверить цены в `kaspi_preview.txt` и `kaspi_export_preview.csv`.
4. Дальше отдельно доделывать Kaspi category mapping, attributes mapping и existing sync.

## Текущее направление после добавления XLSM-шаблонов

Проект теперь должен двигаться не просто к preview, а к строгой подготовке строк под реальные шаблоны Kaspi:

1. WB собирает sellable variants.
2. Official Demiand обогащает характеристики.
3. `kaspi_policy` формирует VAITAN title, цену, stock, lead time, images, описание.
4. `kaspi_templates` проверяет конкретный XLSM-шаблон категории.
5. В export попадают отдельные CSV по шаблонам и аудит заблокированных товаров.

Ближайшая доработка после этого архива: расширять `config/model_specs/*` и mappers в `scripts/cs_kaspi/kaspi_templates/build_template_rows.py`, если Kaspi-аудит показывает missing/invalid поля.
