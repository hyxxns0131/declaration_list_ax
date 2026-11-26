"""칸 격자 → 머리 칸(B/L·모선·통화 …) + 품목 줄. 순수 함수. 담당: KHS [개선] A0-1

엑셀이든 글자 PDF든 같은 규칙으로 읽는다.
- 머리 칸: '라벨' 칸 오른쪽(또는 같은 칸 ':' 뒤)의 값
- 품목 표: 머리글 줄(모델·품명·카톤 …)을 찾아 그 아래를 TOTAL 줄이나 빈 줄까지
라벨·머리글 단어는 아래 표에만 둔다. 서류 양식이 새로 나오면 단어만 추가한다.
"""

import re
from datetime import date, datetime

from pydantic import BaseModel
from pydantic import Field as PField

from app.core.schema.document import DocumentLine

Grid = list[list[object]]


def norm(text: object) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", str(text or "").lower())


# 머리 칸: (칸 이름, 라벨 후보). 긴 라벨을 먼저 본다(producer address > producer).
HEAD_LABELS: list[tuple[str, tuple[str, ...]]] = [
    (
        "manufacturer_address",
        ("produceraddress", "manufactureraddress", "생산자주소", "제조사주소"),
    ),
    ("manufacturer_name", ("producer", "manufacturer", "생산자", "제조사")),
    ("bl_no", ("blno", "blnumber", "billofladingno", "선하증권번호")),
    ("invoice_no", ("invoiceno", "invno", "인보이스번호")),
    ("vessel", ("vesselvoyage", "oceanvessel", "vessel", "모선명", "선명")),
    ("on_board_date", ("shippedonboarddate", "onboarddate", "선적일")),
    ("doc_date", ("invoicedate", "date", "일자")),
    ("currency", ("currency", "통화")),
    ("total_cartons", ("numberofpackages", "noofpackages", "totalpackages", "총포장수")),
    ("total_gross_kg", ("grossweightkg", "grossweight", "총중량")),
]

# 품목 표 머리글: (칸 이름, 머리글 후보). qty_per_carton을 cartons보다 먼저 본다.
LINE_HEADERS: list[tuple[str, tuple[str, ...]]] = [
    ("model", ("model", "modelno", "itemno", "style", "모델")),
    ("description", ("description", "descriptionofgoods", "commodity", "품명")),
    ("qty_per_carton", ("qtyctn", "pcsctn", "qtycarton", "unitsctn", "카톤당", "입수")),
    ("quantity", ("quantity", "qty", "pcs", "totalqty", "수량")),  # 전체 개수(PCS 합계)
    ("cartons", ("ctns", "ctn", "cartons", "카톤")),
    ("net_kg", ("nw", "netweight", "순중량")),
    ("gross_kg", ("gw", "grossweight", "총중량")),
    ("amount", ("amount", "총액", "금액")),
    ("outer_color", ("outercolor", "외색")),
    ("color", ("innercolor", "color", "내색", "색상")),
]

PART_WORDS = ("sparepart", "spare", "parts", "부품", "부분품")
CURRENCY_RE = re.compile(r"\b(USD|CNY|RMB|JPY|EUR|KRW|HKD|VND|THB)\b", re.I)


class GridResult(BaseModel):
    head: dict[str, str] = PField(default_factory=dict)
    lines: list[DocumentLine] = PField(default_factory=list)
    totals: dict[str, float] = PField(default_factory=dict)  # TOTAL 줄
    header_found: bool = False
    head_text: str = ""  # 서류 종류 판별용 첫머리 글자


def to_float(v: object) -> float | None:
    if v is None:
        return None
    if isinstance(v, int | float):
        return float(v)
    s = re.sub(r"[^0-9.\-]", "", str(v))
    try:
        return float(s) if s not in ("", "-", ".") else None
    except ValueError:
        return None


def to_date_text(v: object) -> str:
    if isinstance(v, datetime | date):
        return v.strftime("%Y-%m-%d")
    s = str(v or "").strip()
    m = re.search(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", s)
    return f"{m[1]}-{int(m[2]):02d}-{int(m[3]):02d}" if m else s


def _match(cell_norm: str, keys: tuple[str, ...]) -> bool:
    return any(cell_norm == k or cell_norm.startswith(k) for k in keys)


# 값 자리에 다른 라벨이 붙어 있는 경우(B/L 머리 줄 "Vessel & Voyage: Port of loading: Sailing Date:")를
# 값으로 읽지 않으려고 쓰는 라벨 낱말 (HS 요청 11/26: 모선명에 라벨 글자가 들어간 문제)
_LABEL_WORDS = (
    "portofloading",
    "portofdischarge",
    "placeofreceipt",
    "placeofdelivery",
    "finaldestination",
    "sailingdate",
    "onboarddate",
    "voyageno",
    "vesselvoyage",
    "vessel",
    "shipper",
    "consignee",
    "notifyparty",
    "blno",
)


def looks_like_label(value: object) -> bool:
    """값이 아니라 라벨처럼 보이면 True: 'A: B: C:'처럼 라벨만 이어지거나 라벨 낱말로 시작하고 숫자가 없을 때."""
    if isinstance(value, datetime | date):
        return False
    s = str(value or "").strip()
    if not s:
        return True
    if re.fullmatch(r"(?:[^:]{1,40}:\s*)+", s):
        return True
    n = norm(s)
    return not re.search(r"\d", s) and any(n.startswith(w) for w in _LABEL_WORDS)


def _first_line(value: object) -> str:
    """여러 줄 칸(PDF 표)은 첫 줄만 값으로 본다."""
    return next((ln.strip() for ln in str(value).splitlines() if ln.strip()), "")


def _value_right(row: list[object], i: int) -> str:
    cell = str(row[i] or "")
    if ":" in cell and cell.split(":", 1)[1].strip():
        v = _first_line(cell.split(":", 1)[1])
        return "" if looks_like_label(v) else v
    for c in row[i + 1 :]:
        if c is not None and str(c).strip():
            if isinstance(c, datetime | date):
                return c  # type: ignore[return-value]
            v = _first_line(c)
            # 바로 옆(또는 그 첫 줄)이 다른 라벨이면 값이 없는 것 → 비워 두고 '확인 필요'
            return "" if looks_like_label(v) else v
    return ""


def _parse_head(grid: Grid) -> dict[str, str]:
    head: dict[str, str] = {}
    for row in grid:
        for i, cell in enumerate(row):
            n = norm(str(cell or "").split(":")[0])
            if not n or len(n) > 30:
                continue
            for name, keys in HEAD_LABELS:
                if name not in head and _match(n, keys):
                    v = _value_right(row, i)
                    if v:
                        head[name] = to_date_text(v) if "date" in name else str(v)
                    break
    return head


def _find_header(grid: Grid) -> tuple[int, dict[str, int]] | None:
    for r, row in enumerate(grid):
        cols: dict[str, int] = {}
        for c, cell in enumerate(row):
            n = norm(cell)
            if not n:
                continue
            for name, keys in LINE_HEADERS:
                if name not in cols and _match(n, keys):
                    cols[name] = c
                    break
        if len(cols) >= 3 and ("model" in cols or "description" in cols):
            return r, cols
    return None


def _cell(row: list[object], cols: dict[str, int], name: str) -> object:
    i = cols.get(name)
    return row[i] if i is not None and i < len(row) else None


def parse_grid(grid: Grid) -> GridResult:
    found = _find_header(grid)
    res = GridResult(head_text=" ".join(str(c) for row in grid[:5] for c in row if c))
    if not found:
        res.head = _parse_head(grid)
        return res
    hr, cols = found
    res.header_found = True
    end = len(grid)
    for r in range(hr + 1, len(grid)):
        row = grid[r]
        texts = [norm(c) for c in row]
        if not any(texts):
            if res.lines:
                end = r
                break
            continue
        if any(t.startswith(("total", "합계", "sum")) for t in texts):
            end = r + 1
            for name in ("cartons", "net_kg", "gross_kg", "amount"):
                v = to_float(_cell(row, cols, name))
                if v is not None:
                    res.totals[name] = v
            break
        model = str(_cell(row, cols, "model") or "").strip()
        desc = str(_cell(row, cols, "description") or "").strip()
        if not model and not desc:
            continue
        res.lines.append(
            DocumentLine(
                model=model,
                description=desc,
                qty_per_carton=to_float(_cell(row, cols, "qty_per_carton")),
                quantity=to_float(_cell(row, cols, "quantity")),
                cartons=to_float(_cell(row, cols, "cartons")),
                net_kg=to_float(_cell(row, cols, "net_kg")),
                amount=to_float(_cell(row, cols, "amount")),
                is_part=any(w in norm(desc) for w in PART_WORDS),
                color=str(_cell(row, cols, "color") or "").strip(),
                outer_color=str(_cell(row, cols, "outer_color") or "").strip(),
            )
        )
    # 통화: 머리 칸에 없으면 금액 머리글(Amount (USD))에서
    if "currency" not in res.head and "amount" in cols:
        m = CURRENCY_RE.search(str(grid[hr][cols["amount"]] or ""))
        if m:
            res.head["currency"] = m[1].upper()
    # 머리 칸은 품목 표 밖(위·아래)에서만 찾는다
    res.head = {**_parse_head(grid[end:]), **_parse_head(grid[:hr]), **res.head}
    return res
