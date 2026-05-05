from __future__ import annotations

from .build_attributes import run as build_attributes
from .build_category import run as build_category
from .build_description import run as build_description
from .build_images import run as build_images
from .build_lead_time import run as build_lead_time
from .build_price import run as build_price
from .build_status import run as build_status
from .build_stock import run as build_stock
from .build_title import run as build_title


def run(product: dict) -> dict:
    title = build_title(product)
    product_for_desc = {**product, "kaspi_policy": {"kaspi_title": title}}
    price = build_price(product)
    stock = build_stock(product)
    lead_time = build_lead_time(product)
    images = build_images(product)
    attributes = build_attributes(product)
    category = build_category(product)
    description = build_description(product_for_desc)
    status = build_status(product, price, stock)

    return {
        "product_key": product.get("product_key"),
        "kaspi_policy": {
            "kaspi_title": title,
            "kaspi_price": price,
            "kaspi_stock": stock,
            "lead_time_days": lead_time,
            "kaspi_available": bool(price and stock > 0),
            "kaspi_images": images,
            "kaspi_description": description,
            "kaspi_attributes": attributes,
            "kaspi_category": category,
            "kaspi_category_code": category.get("kaspi_category_code"),
            "kaspi_category_name": category.get("kaspi_category_name"),
            "kaspi_category_path": category.get("kaspi_category_path"),
            "kaspi_category_status": category.get("kaspi_category_status"),
            "kaspi_category_live_ready": category.get("kaspi_category_live_ready"),
            "price_source": "market_policy" if price else None,
            "market_price": product.get("market", {}).get("market_price"),
            "market_price_source": product.get("market", {}).get("market_price_source"),
        },
        "status": status,
    }
