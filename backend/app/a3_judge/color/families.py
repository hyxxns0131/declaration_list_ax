"""색 이름 → 같은 색 묶음(한글·영문 표기). 순수 함수. 담당: LSY [개선] A3-6

시험성적서 검체 색은 한글('노랑'), 'WHITE(흰색)', 선적서류 색은 영문('YELLOW')으로 적히는 경우가 있다.
글자가 달라도 같은 색이면 같은 색으로 보려고 짝을 둔다(record_pick/rank.py 색상 검사).

보수적으로: **같은 이름을 다른 말로 옮긴 것끼리만** 짝짓는다(하늘색 = SKY BLUE, 연두 = YELLOW GREEN, 민트 = MINT).
비슷한 색(하늘색 ↔ BLUE, 연두 ↔ GREEN, 남색 ↔ BLUE, 청록 ↔ TEAL)은 짝짓지 않는다
→ 다르다고 보고 그 실적을 쓰지 않는 쪽(RULES 11-8 색상: 다르면 추가 정밀검사).
실제 서류에 새 표기가 나오면 여기에 짝을 더한다.
"""

# 묶음 이름(영문 대문자) → 같은 색으로 보는 표기들
COLOR_GROUPS: dict[str, tuple[str, ...]] = {
    "WHITE": ("WHITE", "흰색", "하양", "하얀색", "백색", "화이트"),
    "BLACK": ("BLACK", "검정", "검정색", "검은색", "흑색", "블랙"),
    "RED": ("RED", "빨강", "빨간색", "적색", "레드"),
    "BLUE": ("BLUE", "파랑", "파란색", "청색", "블루"),
    "YELLOW": ("YELLOW", "노랑", "노란색", "황색", "옐로", "옐로우"),
    "ORANGE": ("ORANGE", "주황", "주황색", "오렌지"),
    "PURPLE": ("PURPLE", "보라", "보라색", "퍼플"),
    "GREEN": ("GREEN", "초록", "초록색", "녹색", "그린"),
    "GRAY": ("GRAY", "GREY", "회색", "그레이"),
    "BROWN": ("BROWN", "갈색", "브라운"),
    "PINK": ("PINK", "분홍", "분홍색", "핑크"),
    "SILVER": ("SILVER", "은색", "실버"),
    "GOLD": ("GOLD", "금색", "골드"),
    "BEIGE": ("BEIGE", "베이지"),
    "CLEAR": ("CLEAR", "TRANSPARENT", "투명"),
    # 11/28 LSY 확인: 같은 이름을 옮긴 것만(하늘색 ≠ BLUE, 연두 ≠ GREEN)
    "SKY BLUE": ("SKY BLUE", "SKYBLUE", "하늘색", "하늘", "스카이블루"),
    "NAVY": ("NAVY", "남색", "네이비"),
    "YELLOW GREEN": ("YELLOW GREEN", "YELLOWGREEN", "연두", "연두색", "황록색"),
    # 외래어를 소리대로 적은 이름
    "MINT": ("MINT", "민트"),
    "IVORY": ("IVORY", "아이보리"),
    "CREAM": ("CREAM", "크림"),
    "KHAKI": ("KHAKI", "카키"),
    "OLIVE": ("OLIVE", "올리브"),
    "LAVENDER": ("LAVENDER", "라벤더"),
    "CORAL": ("CORAL", "코랄"),
    "BURGUNDY": ("BURGUNDY", "버건디"),
    "WINE": ("WINE", "와인"),
    "CHARCOAL": ("CHARCOAL", "차콜"),
}

_LOOKUP = {name.upper(): group for group, names in COLOR_GROUPS.items() for name in names}


def color_group(word: str) -> str | None:
    """표기 1개 → 묶음 이름. 사전에 없으면 None(글자가 같을 때만 같은 색)."""
    return _LOOKUP.get(word.strip().upper())
