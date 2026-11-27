"""가상 자료 전부 빼기 2차 (HS 지시 11/27 "가상 자료는 다 빼라고"). 담당: KHS

remove_virtual.py 뒤에 남은 것까지: 사람 값이 있던 가상 행, 그 대조 결과·신고건, 유니패스 캐시(가상 B/L),
2번 탭 업로드 후보(가상), 가상 선적 건 서류 원본 사본(data/uploads), 2번 탭 가상 원본(data/registry),
가상 행으로 만든 품목사항 파일(data/item_sheets), 테스트 흔적 폴더(data/test-history-*).
- DB는 지우기 전에 data/backup/<시각>/app.db로 백업, 파일은 같은 백업 폴더로 옮긴다(되돌리기 = 다시 옮기기).
- 감사 기록(audit_log)은 지우지 않는다. samples/·pytest용 자료는 건드리지 않는다.
화면에는 개수만 찍는다.
"""

import io
import shutil
import sqlite3
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402

MARKS = ("VIRTUAL", "BLTEST", "가상", "TEST TRADING")
TABLES = (
    "history_rows",
    "mismatches",
    "declarations",
    "api_cache",
    "uploads",
    "item_files",
    "item_sheets",
    "documents",
    "records",
    "products",
    "factories",
)


def _virtual(text: str) -> bool:
    up = text.upper()
    return any(m.upper() in up for m in MARKS)


def _file_virtual(p: Path) -> bool:
    try:
        if p.suffix.lower() == ".zip":
            with zipfile.ZipFile(p) as z:
                return any(
                    _virtual(n) or _virtual(z.read(n)[:200000].decode("utf-8", "ignore"))
                    for n in z.namelist()
                )
        if p.suffix.lower() in (".json", ".txt", ".csv"):
            return _virtual(p.read_text(encoding="utf-8", errors="ignore"))
        if p.suffix.lower() in (".xlsx", ".xls"):
            data = p.read_bytes()
            if p.suffix.lower() == ".xlsx":
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    return any(
                        _virtual(z.read(n).decode("utf-8", "ignore"))
                        for n in z.namelist()
                        if n.endswith(".xml")
                    )
            return _virtual(data.decode("latin-1", "ignore"))
    except Exception:  # noqa: BLE001 - 못 읽는 파일은 가상으로 보지 않는다
        return False
    return False


def main() -> None:
    s = get_settings()
    data = s.data_path
    db_path = s.path(s.local_db_path)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = data / "backup" / f"{stamp}_all"
    backup.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    dst = sqlite3.connect(backup / "app.db")
    conn.backup(dst)
    dst.close()

    removed: dict[str, int] = {}
    for t in TABLES:
        cols = [r[1] for r in conn.execute(f"pragma table_info({t})")]
        if not cols:
            continue
        rows = conn.execute(f"select rowid, * from {t}").fetchall()
        ids = [r["rowid"] for r in rows if _virtual(str(tuple(r)))]
        for i in range(0, len(ids), 500):
            part = ids[i : i + 500]
            conn.execute(f"delete from {t} where rowid in ({','.join('?' * len(part))})", part)
        if ids:
            removed[t] = len(ids)
    conn.commit()

    # 파일: 가상 선적 건 폴더(옛 백업 DB의 가상 서류 경로) + 내용에 가상 표시가 있는 파일 + 테스트 흔적 폴더
    moved = 0
    old = sorted((data / "backup").glob("2026*_??????/app.db"))
    folders: set[str] = set()
    for b in old:
        try:
            bc = sqlite3.connect(b)
            folders |= {
                r[0].rsplit("/", 1)[0]
                for r in bc.execute("select file_path from documents where bl_no like 'BLTEST%'")
            }
            bc.close()
        except sqlite3.Error:
            pass
    for rel in sorted(folders):
        p = data / rel
        if p.exists():
            (backup / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(backup / rel))
            moved += 1
    for sub in ("registry", "item_sheets", "uploads"):
        for p in list((data / sub).rglob("*")) if (data / sub).exists() else []:
            if p.is_file() and _file_virtual(p):
                rel = p.relative_to(data)
                (backup / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(p), str(backup / rel))
                moved += 1
    locked = 0
    for p in data.glob("test-history-*"):
        try:
            shutil.move(str(p), str(backup / p.name))
            moved += 1
        except OSError:  # 다른 프로그램이 잡고 있거나 권한 없음 — 화면에는 안 쓰는 테스트 흔적
            locked += 1

    # 다시 검사: 남은 가상 표시(감사 기록·원본 적재 표 제외)
    left = 0
    for t in TABLES:
        if [r[1] for r in conn.execute(f"pragma table_info({t})")]:
            left += sum(1 for r in conn.execute(f"select * from {t}") if _virtual(str(tuple(r))))
    conn.close()
    print(f"DB에서 지운 가상 자료: {removed or '없음'}")
    print(f"백업 폴더로 옮긴 가상 파일·폴더: {moved}개 · 백업: {backup}")
    print(f"남은 가상 자료(작업 표): {left}건 · 옮기지 못한 테스트 흔적 폴더 {locked}개(접근 거부)")


if __name__ == "__main__":
    main()
