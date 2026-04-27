# input/kaspi/existing

Put files with products that already exist in Kaspi here.

Supported formats:

```text
.csv
.json
.yml
.yaml
```

Recommended columns:

```text
product_key
kaspi_sku
kaspi_product_id
kaspi_title
kaspi_url
kaspi_price
kaspi_stock
kaspi_available
supplier_key
category_key
brand
model_key
variant_key
official_article
```

Safest mode:

1. Run Build_All.
2. Take `artifacts/kaspi_match_templates/kaspi_existing_template.csv`.
3. Copy it to `input/kaspi/existing/current_kaspi_products.csv`.
4. Fill `kaspi_product_id`, `kaspi_url`, `kaspi_price`, `kaspi_stock`, `kaspi_available` where known.
5. Run Build_All again.

Do not put empty templates here unless you really want them to be read as input.
