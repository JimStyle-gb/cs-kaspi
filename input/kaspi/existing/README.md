# input/kaspi/existing

Сюда кладётся реальная выгрузка существующих товаров из Kaspi-кабинета.

Этот слой нужен только для выбора действия:

```text
есть в Kaspi + есть market-data -> update_candidate
нет в Kaspi + есть market-data -> create_candidate
есть в Kaspi + нет market-data -> pause_candidate
```

Тестовые KSP-TEST/KSP-UPDATE/KSP-PAUSE записи отсутствуют и не должны попадать в рабочую v4-сборку.
