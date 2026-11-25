"""화주 설정(ShipperSettings) — A4 소유. 키 목록은 RULES 11-11. 담당: KHS(모델)"""

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PField


class ShipperSettings(BaseModel):
    model_config = ConfigDict(extra="allow")  # 새 규칙 키는 JUJ가 rules/*.json에 추가

    shipper_id: str  # 가명 id (예: A, B). 실명 금지
    display_name: str  # 예: A사(가전)
    required_docs: list[str] = PField(default_factory=list)
    merge_spare_parts: bool = False
    color_check: bool = False
    max_rows_per_declaration: int | None = None
    sort_by: list[str] = PField(default_factory=list)
