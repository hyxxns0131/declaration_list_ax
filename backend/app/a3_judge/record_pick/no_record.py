"""유효 실적이 없을 때 비고·메모 문구 한 곳. 순수 함수. 담당: LSY [재사용] A3-2 (기존 precise.py)

문구는 RULES 11-2('⚠️ 실적: (이유)')·11-8(만료 → 정밀검사 신청 대상) 형식. 화면·비고가 이 글자를 그대로 보여 준다.
진행 중 정밀검사 표시(기존 waiting_status)는 정밀검사 신청 데이터가 생기면 여기에 더한다(지금은 없음).
"""


def no_valid_record(factory: str) -> str:
    """같은 공장·재질을 모두 포함하는 유효 실적이 없음."""
    return f"이 공장({factory or '주소 기준'})에서 이 재질을 모두 포함하는 유효한 정밀검사 실적 없음 → 정밀검사 대상"


def expired(record_no: str, expires: str) -> str:
    """맞는 실적이 있었지만 만료됨. expires는 'YYYY.MM.DD'."""
    return f"실적 만료 ({record_no}, {expires}) → 정밀검사 신청 대상"


def spec_mismatch(notes: list[str]) -> str:
    """재질 구분이 같은 실적이 없음(유리제·도자기제 등)."""
    head = " / ".join(notes)
    return (head + " → " if head else "") + "같은 재질 구분의 유효한 실적 없음 → 정밀검사 대상"


def color_mismatch(record_no: str, color: str) -> str:
    """실적 성적서 검체 색과 현품 색이 다름(color_check 화주)."""
    return f"{record_no}실적과 현품({color})의 색상이 달라 추가 정밀검사 필요"


NO_DATA = "등록된 실적·같은 모델 이력 없음 → 정밀검사 대상인지 확인"
