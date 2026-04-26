from __future__ import annotations
from scripts.cs_kaspi.core.time_utils import now_iso

def run(products: list[dict]) -> list[dict]:
    result=[]
    for p in products:
        item=dict(p)
        item.setdefault("market",{
            "ozon":{"found":False,"url":None,"price":None,"available":None,"checked_at":now_iso(),"source_hash":None},
            "wb":{"found":False,"url":None,"price":None,"available":None,"checked_at":now_iso(),"source_hash":None},
            "sellable":False,
            "sellable_reason":"market_not_checked",
        })
        result.append(item)
    return result
