# TEST: Kaspi existing update candidate

Тест update-candidate проверен и отключён.

Файл `demiand_existing_kaspi_update_test.csv` оставлен только с заголовком, без активных строк.

Важно:
- не добавлять сюда реальные товары Kaspi;
- для настоящей выгрузки существующих товаров Kaspi использовать отдельный боевой CSV-файл;
- тестовый `KSP-UPDATE-TEST-001` удалён, чтобы проект не считал товар реально существующим в Kaspi.

Ожидаемый результат после Build_All при текущих 3 real manual market items:
- create_candidates: 3
- update_candidates: 0
- pause_candidates: 0
- skipped: 82
