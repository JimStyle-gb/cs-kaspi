# Test filled market worklist

Этот файл добавлен только для проверки importer-слоя `input/market/worklists/`.

Активные тестовые строки:

- `demiand_air_fryer_duos_wifi_black`
- `demiand_air_fryer_waison_wifi_metal`

Ожидаемый результат после `Build_All` вместе с уже существующими 3 manual-market товарами:

- `market records = 5`
- `imported_rows = 2`
- `ready_for_kaspi = 5`
- `create_candidates = 5`
- `skipped = 80`

После проверки этот тестовый файл нужно отключить отдельным патчем, чтобы не оставлять временные данные активными.
