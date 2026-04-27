# Kaspi pause test input

Этот файл добавлен только для проверки pause-логики.

Активная строка имитирует товар, который уже есть в Kaspi, но сейчас НЕ имеет market-data.
После Build_All ожидается:

- create_candidates = 3
- update_candidates = 0
- pause_candidates = 1
- skipped = 81

После проверки этот тестовый файл нужно отключить отдельным патчем, чтобы KSP-PAUSE-TEST-001 не считался реальным товаром Kaspi.
