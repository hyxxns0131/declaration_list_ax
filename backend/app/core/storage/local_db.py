"""로컬 SQLite(data/app.db) 연결과 버전 순서 마이그레이션. 테이블 생성·변경은 여기서만(RULES 7-3). 담당: KHS

기능 폴더는 SQL을 쓰지 않고 이 파일(또는 core/storage의 다른 함수)만 부른다.
새 테이블·칸이 필요하면 PR 설명에 "DB 변경 요청: 테이블, 칸, 이유"를 쓴다.
SCAM/SAMC 원본 적재 표(raw_*)는 scripts/seed/build_local_seed.py가 만든다.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app.core.config import get_settings

# (버전, SQL). 순서대로 한 번만 실행된다. 지난 항목은 고치지 말고 새 버전을 붙인다.
MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        create table if not exists sessions (
          token_hash text primary key,
          remote_token text,            -- Supabase 로그인 토큰(고객사 자료 읽기용). 이 PC에만 저장
          created_at text not null default (datetime('now')),
          expires_at text not null
        );
        create table if not exists login_failures (
          username text primary key,
          count integer not null default 0,
          locked_until text
        );
        create table if not exists audit_log (
          id integer primary key autoincrement,
          at text not null default (datetime('now')),
          action text not null,          -- login, logout, edit, settings_save ...
          target text,
          detail text                    -- 비밀번호·토큰·서류 본문은 남기지 않는다
        );
        """,
    ),
    (
        2,
        """
        create table if not exists documents (
          doc_id text primary key,
          shipper_id text not null,
          folder_id text not null,      -- 폴더 1개 = 선적서류 1건
          bl_no text not null default '',
          doc_type text not null,
          filename text not null,
          file_path text not null,      -- DATA_DIR 기준 상대 경로
          parsed text not null,         -- ParsedDocument JSON
          created_at text not null default (datetime('now'))
        );
        create index if not exists documents_folder on documents(folder_id);
        create table if not exists history_rows (
          row_id text primary key,
          shipper_id text not null,
          bl_no text not null default '',
          seq integer not null default 0, -- 표 순서 (행 이동 반영)
          data text not null,             -- HistoryRow JSON (칸마다 ai/final/evidence)
          updated_at text not null default (datetime('now'))
        );
        create index if not exists history_rows_shipper on history_rows(shipper_id, seq);
        """,
    ),
    (
        3,
        """
        create table if not exists mismatches (
          row_id text not null,
          item text not null,             -- 카톤 수, 금액, 총 포장 수 ...
          data text not null,             -- {"CI": .., "PL": .., "BL": .., "시트": .., "different": bool}
          primary key (row_id, item)
        );
        create table if not exists declarations (
          declaration_id text primary key,
          shipper_id text not null,
          seq integer not null default 0,
          data text not null              -- Declaration JSON
        );
        create index if not exists declarations_shipper on declarations(shipper_id, seq);
        create table if not exists records (
          record_no text primary key,
          shipper_id text not null default '',
          data text not null,             -- Record JSON (+ 서류검사 내역)
          updated_at text not null default (datetime('now'))
        );
        create table if not exists products (
          product_id text primary key,    -- <shipper>:<model>:<receipt_no>
          shipper_id text not null default '',
          model text not null default '',
          data text not null,             -- 수입신고서·성적서에서 읽은 제품별 재질·해외제조업소
          updated_at text not null default (datetime('now'))
        );
        create index if not exists products_model on products(shipper_id, model);
        create table if not exists alerts_sent (
          record_no text not null,
          stage integer not null,         -- 90, 30 (만료 n일 전 단계)
          sent_at text not null default (datetime('now')),
          recipients text not null default '',
          primary key (record_no, stage)
        );
        create table if not exists fx_cache (
          week_key text primary key,      -- 조회 기준일(YYYYMMDD)이 속한 주의 월요일
          data text not null              -- {"USD": {"rate":..,"unit":..,"from":..}, ...}
        );
        create table if not exists api_cache (
          key text primary key,           -- 예: cargo:<B/L>, maker:<회사명>
          data text not null,
          at text not null default (datetime('now'))
        );
        create table if not exists item_files (
          file_id text primary key,
          shipper_id text not null,
          filename text not null,
          file_path text not null,
          row_ids text not null,
          created_at text not null default (datetime('now'))
        );
        create table if not exists uploads (
          upload_id text primary key,     -- 수입신고서·성적서 올리기 1번 = 등록 후보 1묶음
          shipper_id text not null,
          data text not null,             -- 등록 후보 JSON
          created_at text not null default (datetime('now'))
        );
        """,
    ),
]

# 버전 5: 해외제조업소 코드 갱신 관리(A2-5, YHS). 발송 기록은 alerts_sent를 같이 쓰고
# record_no 칸에 "factory_code:<코드>"를 넣어 실적과 구분한다(같은 코드·같은 단계 1회).
MIGRATIONS.append(
    (
        5,
        """
        create table if not exists factories (
          code text primary key,           -- 해외제조업소 코드
          name text not null default '',
          address text not null default '',
          registered_on text,              -- 등록(갱신)일 YYYY-MM-DD, 모르면 null(확인 필요)
          expires_on text,                 -- 등록일 + FACTORY_CODE_VALID_YEARS
          status text not null default '확인 필요',
          source text not null default '', -- 실적·제품 등록·samples(가상)·담당자
          updated_at text not null default (datetime('now'))
        );
        """,
    )
)

# 버전 4: 예전 코드가 같은 이름으로 다른 칸 구성의 작업 표를 만든 DB가 있다(2026-11-25 확인).
# 지우지 않고 legacy_<표>로 이름만 바꾼 뒤 위 2·3번 표를 다시 만든다. raw_* 원본 적재 표는 건드리지 않는다.
REQUIRED_COLUMNS: dict[str, set[str]] = {
    "documents": {"doc_id", "file_path", "parsed"},
    "history_rows": {"row_id", "seq", "data"},
    "records": {"record_no", "shipper_id", "data"},
    "products": {"product_id", "model", "data"},
    "alerts_sent": {"record_no", "stage", "recipients"},
    "item_files": {"file_id", "file_path"},
    "mismatches": {"row_id", "item", "data"},
    "declarations": {"declaration_id", "data"},
}
REPAIR_VERSION = 4


def _repair_legacy(conn: sqlite3.Connection) -> list[str]:
    renamed = []
    for table, need in REQUIRED_COLUMNS.items():
        cols = {r[1] for r in conn.execute(f"pragma table_info({table})")}
        if cols and not need <= cols:
            new = f"legacy_{table}"
            n = 1
            while conn.execute(
                "select 1 from sqlite_master where type='table' and name=?", (new,)
            ).fetchone():
                n += 1
                new = f"legacy_{table}_{n}"
            conn.execute(f"alter table {table} rename to {new}")
            # 예전 인덱스 이름이 새 인덱스와 겹치지 않게 지운다(인덱스는 다시 만들 수 있는 값)
            for (idx,) in conn.execute(
                "select name from sqlite_master where type='index' and tbl_name=? and sql is not null",
                (new,),
            ).fetchall():
                conn.execute(f"drop index if exists {idx}")
            renamed.append(f"{table} → {new}")
    for _, sql in MIGRATIONS:
        if "create table if not exists sessions" not in sql:
            conn.executescript(sql)
    return renamed


def connect() -> sqlite3.Connection:
    path = get_settings().path(get_settings().local_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def migrate() -> int:
    """아직 안 한 마이그레이션을 실행하고 현재 버전을 돌려준다."""
    with connect() as conn:
        conn.execute("create table if not exists schema_version (version integer not null)")
        row = conn.execute("select max(version) from schema_version").fetchone()
        current = row[0] or 0
        for version, sql in MIGRATIONS:
            if version > current:
                conn.executescript(sql)
                conn.execute("insert into schema_version(version) values (?)", (version,))
                current = version
        # 버전 4(예전 표 정리)는 번호 순서와 상관없이 기록이 없으면 한 번 한다(버전 5가 먼저 붙어도 빠지지 않게)
        done = conn.execute(
            "select 1 from schema_version where version = ?", (REPAIR_VERSION,)
        ).fetchone()
        if not done:
            _repair_legacy(conn)
            conn.execute("insert into schema_version(version) values (?)", (REPAIR_VERSION,))
            current = max(current, REPAIR_VERSION)
        return current


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def audit(action: str, target: str = "", detail: str = "") -> None:
    with transaction() as conn:
        conn.execute(
            "insert into audit_log(action, target, detail) values (?, ?, ?)",
            (action, target, detail),
        )
