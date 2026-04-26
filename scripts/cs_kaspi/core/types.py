from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class OfficialData:
    exists: bool = False
    status: str = "missing"
    product_id: str | None = None
    url: str | None = None
    title: str = ""
    description: str = ""
    images: list[str] = field(default_factory=list)
    specs: dict[str, Any] = field(default_factory=dict)
    package: dict[str, Any] = field(default_factory=dict)
    checked_at: str | None = None
    source_hash: str | None = None
