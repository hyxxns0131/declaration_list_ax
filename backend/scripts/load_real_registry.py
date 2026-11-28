"""2번 탭 등록 정보(실적·제품)를 HS가 DB에 넣은 실제 자료로 채운다 (HS 지시 11/27). 담당: KHS

읽기만: 로컬 원본 적재 표(raw_json·raw_sheet_rows, Supabase samc_*를 PM이 받아 둔 것). Supabase에 쓰지 않는다.
- 수입신고서·시험성적서 판독 JSON(raw_json category=intake) → YHS 공개 함수 a2 upload.create_upload·commit_upload 그대로
  (a2 폴더는 고치지 않는다. 판독 JSON 형식이 a2의 .json 입력과 같다).
- 실적DB 탭('A기업 실적DB'·'B기업 실적DB') → 아직 없는 실적번호만 a2 records.save로 등록(근거 HISTORY).
화주 구분: 화주 표기(A기업 → A, B기업 → B). 화면에는 개수만 찍는다.

실행: cd backend && .venv/Scripts/python scripts/load_real_registry.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.a2_registry.records import service as records  # noqa: E402
from app.a2_registry.upload.service import commit_upload, create_upload  # noqa: E402
from app.core.schema.fields import Evidence  # noqa: E402
from app.core.schema.record import Record, SamplePart  # noqa: E402
from app.core.storage.local_db import transaction  # noqa: E402


def _sid(label: str) -> str:
    return re.sub(r"[^A-Za-z]", "", label or "")[:1].upper()


def _date(v: object) -> str | None:
    d = records.to_date(str(v)) if v not in (None, "") else None
    return d.isoformat() if d else None


def _no_nulls(v: object) -> object:
    if isinstance(v, dict):
        return {k: ("" if x is None else _no_nulls(x)) for k, x in v.items()}
    if isinstance(v, list):
        return [_no_nulls(x) for x in v]
    return v


def load_json() -> dict:
    with transaction() as conn:
        rs = conn.execute(
            "select path, shipper, body from raw_json where category = 'intake'"
        ).fetchall()
    by_sid: dict[str, list[tuple[str, bytes]]] = {}
    for r in rs:
        body = json.loads(r["body"]) if isinstance(r["body"], str) else r["body"]
        if not isinstance(body, dict) or body.get("kind") not in ("수입신고서", "시험성적서"):
            continue
        sid = _sid(r["shipper"])
        if sid not in ("A", "B"):
            continue
        body = _no_nulls(body)  # a2 TestReport가 null 글자 칸을 받지 않음(YHS 요청) → 빈 글자로
        name = Path(r["path"]).stem + ".json"
        by_sid.setdefault(sid, []).append(
            (name, json.dumps(body, ensure_ascii=False).encode("utf-8"))
        )
    out = {}
    for sid, files in by_sid.items():
        up = create_upload(sid, files, set())
        res = commit_upload(up["upload_id"], [])
        out[sid] = {
            "files": len(files),
            "products": res["products"],
            "records": len(res["records"]),
            "skipped": len(res["skipped"]),
        }
    return out


def load_sheet() -> dict:
    out: dict[str, int] = {}
    with transaction() as conn:
        rs = conn.execute(
            "select sheet, cells from raw_sheet_rows where sheet in ('A기업 실적DB', 'B기업 실적DB')"
        ).fetchall()
    for r in rs:
        cells = json.loads(r["cells"]) if isinstance(r["cells"], str) else r["cells"]
        sid = _sid(r["sheet"])
        no = re.sub(r"[^0-9]", "", str(cells.get("실적접수번호") or ""))
        if len(no) < 8:
            continue
        try:
            records.get_record(no)
            continue  # 이미 있음(판독 JSON에서 들어옴)
        except Exception:  # noqa: BLE001 - 없으면 새로 만든다
            pass
        maker = str(cells.get("제조사") or "").strip()
        m = re.search(r"\(([A-Z]{2}\d{6,})\)", maker)
        mats = [
            x.strip() for x in re.split(r"[,·/]", str(cells.get("검체 재질") or "")) if x.strip()
        ]
        rec = Record(
            record_no=no,
            factory_code=m.group(1) if m else "",
            factory_name=re.sub(r"\s*\([A-Z]{2}\d{6,}\)\s*", "", maker),
            materials=sorted(set(mats)),
            spec_class=str(cells.get("재질 구분") or cells.get("규격 구분") or ""),
            sample_parts=[
                SamplePart(
                    material=str(cells.get("검체 재질") or ""),
                    part=str(cells.get("부품") or ""),
                    color=str(cells.get("색상") or ""),
                )
            ],
            applied_on=_date(cells.get("신청일")),
            approved_on=_date(cells.get("승인일")),
            product_names=[str(cells.get("제품명"))] if cells.get("제품명") else [],
            evidence=[
                Evidence(source="HISTORY", ref=r["sheet"], note="실적DB 탭(검역 이력 공유본)")
            ],
        )
        records.save(rec, sid)
        out[sid] = out.get(sid, 0) + 1
    return out


def main() -> None:
    js = load_json()
    sh = load_sheet()
    for sid in sorted(set(js) | set(sh)):
        j = js.get(sid, {})
        print(
            f"화주 {sid}: 판독 JSON {j.get('files', 0)}개 → 제품 {j.get('products', 0)}개·실적 {j.get('records', 0)}개"
            f"(접수번호 없어 건너뜀 {j.get('skipped', 0)}) · 실적DB 탭에서 실적 {sh.get(sid, 0)}개 추가"
        )


if __name__ == "__main__":
    main()
