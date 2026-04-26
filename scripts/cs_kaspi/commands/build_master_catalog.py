from __future__ import annotations
from scripts.cs_kaspi.core.file_paths import ensure_base_dirs, get_path, ROOT
from scripts.cs_kaspi.core.write_json import write_json
from scripts.cs_kaspi.core.read_yaml import read_yaml
from scripts.cs_kaspi.catalog.build_master_catalog import run as build_master
from scripts.cs_kaspi.markets.merge_market_data import run as merge_market
from scripts.cs_kaspi.kaspi_policy.build_kaspi_offer import run as build_offer
from scripts.cs_kaspi.kaspi_policy.build_kaspi_status import run as build_status

def run() -> dict:
    ensure_base_dirs()
    demo_product={
        "product_key":"demiand_air_fryer_sanders_max_black",
        "supplier_key":"demiand",
        "brand":"DEMIAND",
        "category_key":"air_fryers",
        "model_key":"sanders_max",
        "variant_key":"black",
        "official":{"exists":True,"status":"active","product_id":"demiand_sanders_max_black","url":"https://demiand.ru/product/example/","title":"Аэрогриль DEMIAND Sanders Max черный","description":"Официальное описание товара","images":["https://example.com/image.jpg"],"specs":{"volume_l":6,"programs":12,"wifi":True},"package":{"recipe_book":True},"checked_at":None,"source_hash":None},
        "model_specs": read_yaml(ROOT / "config" / "model_specs" / "demiand_air_fryers.yml"),
    }
    products=merge_market([demo_product])
    for p in products:
        p["kaspi_policy"]=build_offer(p)
        p["status"]=build_status(p)
        p["changes"]={"last_checked_at":None,"last_changed_at":None,"official_hash":None,"market_hash":None,"kaspi_hash":None,"changed_official":False,"changed_market":False,"changed_kaspi":False}
        p["kaspi_match"]={"exists_in_kaspi":False,"match_status":"not_matched","kaspi_product_id":None,"match_confidence":"none"}
        p["meta"]={"created_at":None,"updated_at":None,"notes":""}
    catalog=build_master(products,["demiand"],["air_fryers"])
    write_json(get_path("artifacts_state_dir") / "master_catalog.json", catalog)
    summary={"built_at":catalog["meta"]["built_at"],"total_products":len(catalog["products"]),"suppliers":{"demiand":len(catalog["products"])},"categories":{"air_fryers":len(catalog["products"])},"lifecycle_status":{"catalog_only":sum(1 for p in catalog["products"] if p["status"]["lifecycle_status"]=="catalog_only"),"market_active":0,"kaspi_ready":sum(1 for p in catalog["products"] if p["status"]["lifecycle_status"]=="kaspi_ready"),"kaspi_active":0,"kaspi_paused":0,"needs_review":0,"blocked":0}}
    write_json(get_path("artifacts_state_dir") / "master_catalog_summary.json", summary)
    return catalog

if __name__ == "__main__":
    run()
