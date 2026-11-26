"""실제 선적서류에서 화주(수입자) 회사 표기를 모아 PC 전용 data/mask_names.json을 만든다(수동 실행). 담당: KHS

로직은 app/core/mask_names.py에 있다(백엔드가 목록이 없으면 자동으로 같은 일을 한다).
실행: cd backend && .venv/Scripts/python scripts/make_mask_names.py [--check]
  --check: 만든 목록으로 실제 서류 글자를 가린 뒤, 수하인 칸이 가려졌는지·수출자 칸을 잘못 가렸는지 수치만 찍는다.
실제 이름은 화면·로그·저장소 어디에도 찍지 않는다. 화주별 개수와 종류(국문/영문/약칭)만.
"""

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.mask_names import (  # noqa: E402
    OTHER,
    PARTY,
    _doc_texts,
    _kind,
    _login,
    _norm,
    _ok,
    _values,
    build,
    save,
)
from app.core.masking import MASK, mask_file, mask_text  # noqa: E402


def check(token: str, names: dict[str, list[str]]) -> None:
    """수치만: 수하인·수입자 칸 값이 가려졌는지, 수출자·제조사 칸 값을 잘못 가렸는지, 이름마다 쓰인 서류 수."""
    every = sorted({n for v in names.values() for n in v}, key=len, reverse=True)
    docs = _doc_texts(token)
    pv = pm = ov = om = 0
    for _shipper, text in docs:
        lines = [ln for ln in text.splitlines() if ln.strip()]
        for v in _values(lines, PARTY):
            if _ok(v):
                pv += 1
                pm += MASK in mask_text(v, every)
        for v in _values(lines, OTHER):
            if _ok(v):
                ov += 1
                om += MASK in mask_text(v, every)
    print(f"수하인·수입자 칸 값 {pv}개 중 가려진 값 {pm}개")
    print(f"수출자·제조사·선사 칸 값 {ov}개 중 가려진 값 {om}개 (0에 가까워야 함)")
    # 이름마다: 자기 화주 서류 몇 개 / 다른 화주 서류 몇 개에 나오는지, 낱말 수 (이름은 찍지 않는다)
    by = defaultdict(list)
    for shipper, text in docs:
        by[re.sub(r"[^A-Za-z]", "", shipper)[:1].upper()].append(_norm(text))
    for sid, ns in names.items():
        rows = []
        for n in ns:
            k = _norm(n)
            own = sum(k in t for t in by.get(sid, []))
            oth = sum(k in t for s2, ts in by.items() if s2 != sid for t in ts)
            rows.append(f"{len(n.split())}낱말·{len(k)}자·자기 {own}/다른 {oth}")
        print(f"화주 {sid}: " + " | ".join(rows))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    token = _login()
    if not token:
        print("Supabase 로그인 실패 — .env 관리자 계정 확인")
        return
    names = build(token)
    labels = {
        k: f"화주{i + 1}" for i, k in enumerate(sorted(names))
    }  # 화면에는 가명 표기도 바꿔 찍는다
    save(names)
    for k, v in names.items():
        kinds = Counter(_kind(n) for n in v)
        print(f"{labels[k]}: 이름 {len(v)}개 · {dict(kinds)}")
    print(f"저장: {mask_file()} (PC 안에만, .gitignore)")
    if args.check:
        by_id = {re.sub(r"[^A-Za-z]", "", k)[:1].upper() or k: v for k, v in names.items()}
        check(token, by_id)


if __name__ == "__main__":
    main()
