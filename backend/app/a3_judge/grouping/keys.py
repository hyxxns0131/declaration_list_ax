"""신고건 키: 모선(화물관리번호 앞 11자리)·제조업소·재질·색상. 순수 함수. 담당: LSY [개선] A3-4

반드시 조건: 같은 모선, 같은 제조업소(RULES 11-6). 재질·색상은 화주 설정으로 켜고 끈다.
화물관리번호가 아직 없으면(유니패스 전) 모선명으로 묶고 경고를 남긴다 — 확인 필요 2.
"""

from app.a3_judge.history_lookup.model_key import split_maker
from app.core.schema.declaration import DeclarationKey
from app.core.schema.history import C_CARGO, C_MAKER, C_MATERIAL, C_VESSEL, COLOR_COLUMN, HistoryRow
from app.core.schema.shipper import ShipperSettings

VESSEL_KEY_LEN = 11  # 화물관리번호 앞 11자리 = 동일 모선 (미팅 11/24, 확인 필요 2)
NO_CARGO_PREFIX = "모선명:"


def vessel_key(row: HistoryRow) -> str:
    cargo = row.text(C_CARGO).replace("-", "").strip()
    if cargo:
        return cargo[:VESSEL_KEY_LEN]
    vessel = row.text(C_VESSEL).strip().upper()
    return f"{NO_CARGO_PREFIX}{vessel}" if vessel else ""


def factory_key(row: HistoryRow) -> str:
    name, code = split_maker(row.text(C_MAKER))
    return code or name


def material_key(row: HistoryRow) -> str:
    """재질 칸이 '○○ 자료 추가 필요'면 아직 재질이 없는 것(빈 키) — 문구마다 신고건이 갈리지 않게."""
    text = row.text(C_MATERIAL)
    return "" if "자료 추가 필요" in text else text


def row_key(row: HistoryRow, settings: ShipperSettings) -> DeclarationKey:
    return DeclarationKey(
        vessel_key=vessel_key(row),
        factory_code=factory_key(row),
        material=material_key(row) if getattr(settings, "group_by_material", True) else "",
        color=row.text(COLOR_COLUMN) if getattr(settings, "group_by_color", False) else None,
    )


def key_tuple(k: DeclarationKey) -> tuple[str, str, str, str]:
    return (k.vessel_key, k.factory_code, k.material, k.color or "")
