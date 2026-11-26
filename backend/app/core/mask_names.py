"""화주명 가리기 목록 만들기 (HS 결정 11/26: "DB에 있으니 끌고 오면 된다"). 담당: KHS

- Supabase samc_files·samc_texts·samc_sheet_rows를 읽기만 해서(프로그램 계정 로그인) 실제 선적서류의
  수하인·구매자·수입자·통지처 칸에서 화주 회사 표기를 모아 PC 전용 DATA_DIR/mask_names.json에만 저장한다.
- 이름은 로그·응답·화면 어디에도 내보내지 않는다. 밖으로 나가는 것은 개수뿐(status()).
- 자동 만들기: 서버가 뜰 때 1번(뒤에서, 실패해도 서버는 뜬다) + core/llm.py가 목록 없음을 알았을 때 1번.
  실패(로그인 불가·네트워크)하면 목록 없음 그대로 → AI 전송은 계속 막힌다. 30분 지나면 다시 시도.
- 수동: backend/scripts/make_mask_names.py [--check]
"""

import json
import re
import sys
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.masking import all_names, load_names, mask_file

RETRY_SEC = 30 * 60
_LOCK = threading.Lock()
_state: dict = {"last_try": 0.0, "last_error": ""}


def _auto_enabled() -> bool:
    """테스트 중에는 Supabase에 붙지 않는다."""
    return "pytest" not in sys.modules


# 화주 쪽 이름이 오는 칸
PARTY = re.compile(
    r"(CONSIGNEE|BUYER|SOLD\s*TO|MESSRS\.?|IMPORTER|ACCOUNTEE|"
    r"수입자|수하인|납세의무자|구매자)\s*[:：]?\s*(.*)",
    re.I,
)
# 통지처: 포워더·관세사인 경우가 많아 다른 화주 서류에도 나오면 뺀다
NOTIFY = re.compile(r"(NOTIFY\s*PARTY|NOTIFY)\s*[:：]?\s*(.*)", re.I)
# 화주가 아닌 쪽(여기 나온 이름은 목록에서 뺀다)
OTHER = re.compile(
    r"(SHIPPER|EXPORTER|SELLER|MANUFACTURER|PRODUCER|BENEFICIARY|CARRIER|FORWARD|AGENT|수출자|제조사|생산자)"
    r"\s*[:：]?\s*(.*)",
    re.I,
)
GENERIC = {
    "KOREA", "SOUTHKOREA", "REPUBLICOFKOREA", "TOORDER", "TOTHEORDEROF", "ORDER", "SAMEASCONSIGNEE",
    "SAMEASABOVE", "SAMEAS", "NA", "NONE", "COLTD", "CORPORATION", "INC", "LTD", "SAMC", "TEL", "FAX",
    "ADDRESS", "ADD", "SEOUL", "BUSAN", "PUSAN", "INCHEON", "PYEONGTAEK", "ULSAN", "GWANGYANG", "KWANGYANG",
    "POHANG", "GYEONGGI", "KYUNGGI", "주식회사", "대한민국", "한국", "서울", "부산", "인천",
}  # fmt: skip
SUFFIX = re.compile(
    r"(주식회사|\(주\)|㈜|CO\.?,?\s*LTD\.?|CO\.?|LTD\.?|INC\.?|CORP\.?|CORPORATION|LIMITED)", re.I
)
CUT = re.compile(r"(\s{2,}|,|\bTEL\b|\bFAX\b|\bADD(RESS)?\b|\bATTN\b|\d{2,}|\||\t)", re.I)


def _norm(t: str) -> str:
    return re.sub(r"[^0-9A-Z가-힣]", "", t.upper())


def _select(table: str, params: dict, token: str) -> list[dict]:
    s = get_settings()
    h = {"apikey": s.supabase_anon_key, "Authorization": f"Bearer {token}"}
    out, offset = [], 0
    while True:
        q = {"select": "*", "limit": "1000", "offset": str(offset), **params}
        r = httpx.get(f"{s.supabase_url}/rest/v1/{table}", params=q, headers=h, timeout=120)
        r.raise_for_status()
        rows = r.json()
        out += rows
        if len(rows) < 1000:
            return out
        offset += 1000


def _clean(raw: str) -> str:
    """칸 값에서 회사 이름 부분만: 주소·전화·번호 앞에서 자른다."""
    t = CUT.split(raw.strip(), maxsplit=1)[0].strip(" .:-/")
    return re.sub(r"\s+", " ", t)


def _ok(name: str) -> bool:
    n = _norm(name)
    core = _norm(SUFFIX.sub(" ", name))
    return len(core) >= 3 and n not in GENERIC and core not in GENERIC


def _values(lines: list[str], pattern: re.Pattern) -> list[str]:
    """라벨 뒤 값. 같은 줄이 비면 다음 줄."""
    out = []
    for i, line in enumerate(lines):
        m = pattern.search(line)
        if not m:
            continue
        v = m.group(2).strip()
        if not _norm(v) and i + 1 < len(lines):
            v = lines[i + 1]
        v = _clean(v)
        if v:
            out.append(v)
    return out


def _doc_texts(token: str) -> list[tuple[str, str]]:
    """[(화주 표기, 서류 글자)] — 선적서류·접수 서류만."""
    files = _select("samc_files", {"category": "in.(shipping_docs,intake)"}, token)
    who = {f["path"]: str(f.get("shipper") or "") for f in files if f.get("shipper")}
    by_path: dict[str, list[str]] = defaultdict(list)
    for t in _select("samc_texts", {"select": "path,text"}, token):
        if t["path"] in who and t.get("text"):
            by_path[t["path"]].append(t["text"])
    rows = _select(
        "samc_sheet_rows",
        {"select": "workbook,cells", "sheet": "not.in.(아이템마스터,라벨마스터)"},
        token,
    )
    for r in rows:
        if r["workbook"] in who:
            cells = r.get("cells") or {}
            by_path[r["workbook"]].append(
                "  ".join(str(v) for v in cells.values() if v not in (None, ""))
            )
    return [(who[p], "\n".join(ts)) for p, ts in by_path.items()]


def build(token: str) -> dict[str, list[str]]:
    docs = _doc_texts(token)
    party: dict[str, Counter] = defaultdict(Counter)
    other: set[str] = set()
    notify: set[str] = set()
    for shipper, text in docs:
        lines = [ln for ln in text.splitlines() if ln.strip()]
        for v in _values(lines, PARTY):
            if _ok(v):
                party[shipper][v.upper()] += 1
        for v in _values(lines, NOTIFY):
            if _ok(v):
                party[shipper][v.upper()] += 1
                notify.add(v.upper())
        for v in _values(lines, OTHER):
            other.add(_norm(SUFFIX.sub(" ", v)))
    out: dict[str, list[str]] = {}
    for shipper, cnt in party.items():
        names: set[str] = set()
        for name in cnt:
            core = SUFFIX.sub(" ", name).strip(" .,")
            core = re.sub(r"\s+", " ", core)
            if _norm(core) in other or _norm(name) in other:
                continue  # 수출자·제조사·선사 쪽에도 나오는 이름은 화주가 아니다
            names.add(name)
            if _ok(core):
                names.add(core)
        out[shipper] = sorted(names, key=len, reverse=True)
    # 걸러내기: 문장처럼 긴 값(6낱말·40자 넘음).
    # 수하인·구매자·수입자 값은 수입자 그 자체라 다른 화주 서류에 나와도 둔다(가리는 쪽이 안전, HS 결정 11/26).
    # 통지처에만 나온 값은 다른 화주 서류에도 나오면 포워더·관세사로 보고 뺀다.
    consignee = {
        v.upper() for _s, text in docs for v in _values(text.splitlines(), PARTY) if _ok(v)
    }
    notify_only = {n for n in notify if n not in consignee}
    generic = _generic_words()
    texts: dict[str, list[str]] = defaultdict(list)
    for shipper, text in docs:
        texts[shipper].append(_norm(text))
    for shipper, names_ in out.items():
        others = [t for s2, ts in texts.items() if s2 != shipper for t in ts]
        out[shipper] = [
            n
            for n in names_
            if len(n.split()) <= 6
            and len(_norm(n)) <= 40
            and not (n in notify_only and any(_norm(n) in t for t in others))
            and _norm(n) not in generic
        ]
        # 공유 자료의 서류에는 실제 이름 대신 화주 가명 표기(예: A기업)가 들어간 곳이 있다 → 그 표기도 가린다
        if shipper not in out[shipper]:
            out[shipper].append(shipper)
    return out


def _generic_words() -> set[str]:
    """흔한 낱말·서류 라벨: 이 저장소의 코드·가상 샘플·프롬프트에 통째로 나오는 낱말과 라벨 문구.
    이것과 같은 '이름'은 실제 회사명이 아니라 라벨(PORT OF DISCHARGE 등)이 잘못 잡힌 것이라 뺀다(11/26 dev 점검)."""
    from openpyxl import load_workbook

    from app.a0_reader.extract.grid_parse import HEAD_LABELS, LINE_HEADERS

    root = Path(__file__).resolve().parents[3]
    words: set[str] = {k.upper() for _n, keys in [*HEAD_LABELS, *LINE_HEADERS] for k in keys}
    texts: list[str] = []
    for pattern in (
        "backend/app/**/*.py",
        "backend/prompts/**/*.md",
        "frontend/**/*.tsx",
        "frontend/lib/**/*.ts",
    ):
        for p in root.glob(pattern):
            if (
                "node_modules" not in p.parts and "tests" not in p.parts
            ):  # 테스트의 가짜 이름은 빼고
                texts.append(p.read_text(encoding="utf-8", errors="ignore"))
    for p in (root / "samples").rglob("*.xlsx"):
        wb = load_workbook(p, read_only=True, data_only=True)
        for ws in wb.worksheets:
            for r in ws.iter_rows(values_only=True):
                texts.append(" ".join(str(c) for c in r if c is not None))
    for t in texts:
        words |= {_norm(w) for w in re.findall(r"[A-Za-z가-힣][A-Za-z가-힣0-9]{2,}", t)}
        # 여러 낱말 라벨(Port of Discharge)·가상 회사명도 통째로
        words |= {_norm(m) for m in re.findall(r"[A-Za-z][A-Za-z .,&()-]{4,60}", t)}
    return words - {""}


def _kind(name: str) -> str:
    if re.search("[가-힣]", name):
        return "국문"
    if SUFFIX.search(name):
        return "영문"
    return "약칭(회사 형태 뺀 이름)"


def save(names: dict[str, list[str]]) -> int:
    """화주 표기(A기업) → 화주 id(A)로 바꿔 PC 전용 파일에 저장. 저장한 이름 수."""
    by_id = {re.sub(r"[^A-Za-z]", "", k)[:1].upper() or k: v for k, v in names.items()}
    path = mask_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(by_id, ensure_ascii=False, indent=1), encoding="utf-8")
    return sum(len(v) for v in by_id.values())


def _login() -> str | None:
    from app.core.auth.service import _supabase_login

    s = get_settings()
    if not (s.supabase_url and s.supabase_anon_key and s.admin_username and s.admin_password):
        return None
    return _supabase_login(s.admin_username, s.admin_password)


def ensure(force: bool = False) -> int:
    """목록이 없으면 DB에서 만들어 저장. 있는 이름 수(0 = 없음·실패). 이름은 돌려주지 않는다."""
    if all_names() and not force:
        return len(all_names())
    if not _auto_enabled():
        return 0
    with _LOCK:
        if all_names() and not force:
            return len(all_names())
        if not force and time.time() - _state["last_try"] < RETRY_SEC:
            return 0
        _state["last_try"] = time.time()
        try:
            token = _login()
            if not token:
                _state["last_error"] = "Supabase 로그인 불가(.env 계정·연결 확인)"
                return 0
            n = save(build(token))
            _state["last_error"] = ""
            return n
        except Exception as e:  # 네트워크·형식 오류: 목록 없음 그대로(AI 전송 막힘 유지)
            _state["last_error"] = type(e).__name__
            return 0


def ensure_in_background() -> None:
    """서버가 뜰 때: 목록이 없으면 뒤에서 만든다(서버 시작을 막지 않는다)."""
    if all_names() or not _auto_enabled():
        return
    threading.Thread(target=ensure, name="mask-names", daemon=True).start()


def status() -> dict:
    """연결 설정 화면용: 있음/없음과 개수만."""
    names = load_names()
    n = sum(len(v) for v in names.values())
    return {
        "exists": n > 0,
        "count": n,
        "shippers": len(names),
        "path": str(mask_file()),
        "last_error": _state["last_error"],
    }
