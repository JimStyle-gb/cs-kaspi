CS-Kaspi Kaspi existing input — test file disabled

Этот файл намеренно оставлен только с заголовком, без тестовых товаров.

Почему:
- patch 09 уже проверил Kaspi-match на 3 тестовых товарах;
- активные KSP-TEST записи нельзя оставлять в рабочем проекте;
- иначе будущие draft exports будут считать 3 товара уже существующими в Kaspi, хотя это были fake/test записи.

Для реальной работы:
1. Не заполняй этот test-файл.
2. Создай отдельный рабочий файл рядом, например:
   input/kaspi/existing/kaspi_existing_current.csv
3. Заполняй его реальными товарами из Kaspi.
4. Минимально полезные поля:
   product_key, kaspi_sku, kaspi_product_id, kaspi_title, kaspi_url, kaspi_price, kaspi_stock, kaspi_available

Если нужно снова проверить update-логику, можно временно добавить строки в этот файл,
но после проверки снова очистить его до одного заголовка.
