"""색 이름 짝: 확실히 같은 이름끼리만. 비슷한 색은 짝짓지 않는다(보수적). 가상 값."""

from app.a3_judge.color.families import color_group
from app.a3_judge.record_pick.rank import _color_ok
from app.core.schema.record import Record, SamplePart


def _rec(*colors: str) -> Record:
    return Record(
        record_no="R-1",
        sample_parts=[SamplePart(material="도자기제", part="", color=c) for c in colors],
    )


def test_korean_english_pairs():
    assert color_group("노랑") == color_group("yellow") == "YELLOW"
    assert color_group("흰색") == color_group("WHITE") == "WHITE"
    assert color_group("하늘색") == color_group("SKY BLUE") == "SKY BLUE"
    assert (
        color_group("연두")
        == color_group("yellow green")
        == color_group("황록색")
        == "YELLOW GREEN"
    )
    assert color_group("민트") == "MINT" and color_group("청록") is None  # 애매한 이름은 짝 없음


def test_record_with_many_korean_colors():
    """검체가 한글 여러 색(세트 제품) → 서류 영문 색 하나라도 맞으면 통과."""
    r = _rec("노랑", "파랑", "연두", "하늘색", "보라", "빨강", "주황")
    assert _color_ok(r, "YELLOW") is True
    assert _color_ok(r, "BLUE") is True
    assert _color_ok(r, "하늘색") is True  # 글자가 같으면 통과
    assert _color_ok(r, "SKY BLUE") is True  # 하늘색 = SKY BLUE (같은 이름을 옮긴 것)
    assert _color_ok(r, "YELLOW GREEN") is True  # 연두
    assert _color_ok(r, "WHITE") is False  # 검체 7색 모두 사전에 있고 WHITE 없음


def test_similar_colors_not_merged():
    assert _color_ok(_rec("하늘색"), "BLUE") is False
    assert _color_ok(_rec("연두"), "GREEN") is False
    assert _color_ok(_rec("남색"), "BLUE") is False
    assert _color_ok(_rec("하늘색"), "LIGHT BLUE") is None  # 사전에 없는 이름 → 확인 필요


def test_unknown_color_name_needs_check():
    """사전에 없는 이름(FOGGY GRAY)은 다름이라 단정하지 않고 None(색상 확인 필요). 글자가 같으면 같음."""
    assert _color_ok(_rec("회색"), "FOGGY GRAY") is None
    assert _color_ok(_rec("FOGGY GRAY"), "foggy gray") is True
    assert (
        _color_ok(_rec("노랑", "FOGGY GRAY"), "BLUE") is None
    )  # 검체 중 모르는 이름이 있으면 확인
    assert _color_ok(_rec("노랑"), "BLUE") is False  # 둘 다 사전에 있고 다르면 다름
