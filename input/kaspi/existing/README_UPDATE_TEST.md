# TEST: Kaspi existing update candidate

Временный тестовый файл для проверки update-candidate.

Активная строка:
- product_key: demiand_air_fryer_tison_wifi_metal
- kaspi_product_id: KSP-UPDATE-TEST-001

Ожидаемый результат после Build_All при текущих 3 real manual market items:
- create_candidates: 2
- update_candidates: 1
- pause_candidates: 0
- skipped: 82

После проверки этот тестовый файл нужно отключить отдельным patch, чтобы KSP-UPDATE-TEST-001 не остался как будто реальный товар Kaspi.
