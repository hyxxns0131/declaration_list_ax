"""화주 등록부(별칭·통관고유부호) 저장. 담당: JUJ [신규] A4-1

- 위치: DATA_DIR/shipper_registry.json (data/는 git 제외). 통관고유부호는 여기에만 둔다.
  규칙 파일(rules/shippers/*.json)·파일명·로그·audit에는 쓰지 않는다.
- 쓰기: 같은 폴더 임시 파일 → fsync → os.replace (반쯤 쓴 파일이 남지 않음).
- 잠금: DATA_DIR/shipper_registry.lock 에 OS 파일 잠금(Windows msvcrt, 그 밖 fcntl) + 프로세스 안 threading.Lock.
  잠금은 '파일이 있느냐'가 아니라 OS 잠금이라 강제 종료 시 OS가 풀어 준다. 잠금 파일은 지우지 않는다.
- 항목 상태: pending(등록 중) → active, 강제 종료로 남은 pending은 reconcile()이 정리, deleted(화주 삭제).
"""

import json
import os
import sys
import tempfile
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings

FILE_NAME = "shipper_registry.json"
LOCK_NAME = "shipper_registry.lock"

PENDING = "pending"
ACTIVE = "active"
ABANDONED = "abandoned"
DELETED = "deleted"

_thread_lock = threading.Lock()


class LockTimeout(Exception):
    """잠금을 정해진 시간 안에 얻지 못함."""


def _dir() -> Path:
    return get_settings().data_path


def registry_path() -> Path:
    return _dir() / FILE_NAME


def empty() -> dict:
    return {"version": 1, "last_seq": 0, "shippers": {}}


def load() -> dict:
    path = registry_path()
    if not path.exists():
        return empty()
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("version", 1)
    data.setdefault("last_seq", 0)
    data.setdefault("shippers", {})
    return data


def save(data: dict) -> None:
    """원자적 쓰기: 임시 파일에 다 쓰고 fsync 한 뒤 교체한다."""
    path = registry_path()
    fd, tmp = tempfile.mkstemp(prefix=".shipper_registry.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _try_os_lock(f: BinaryIO) -> bool:
    f.seek(0)
    if sys.platform == "win32":
        import msvcrt

        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    import fcntl

    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _os_unlock(f: BinaryIO) -> None:
    f.seek(0)
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


@contextmanager
def locked(timeout: float = 5.0) -> Iterator[None]:
    """등록부를 바꾸는 동안 다른 스레드·프로세스가 끼어들지 못하게 한다."""
    deadline = time.monotonic() + timeout
    if not _thread_lock.acquire(timeout=timeout):
        raise LockTimeout
    try:
        lock_file = _dir() / LOCK_NAME
        with open(lock_file, "a+b") as f:
            while not _try_os_lock(f):
                if time.monotonic() >= deadline:
                    raise LockTimeout
                time.sleep(0.05)
            try:
                yield
            finally:
                _os_unlock(f)
    finally:
        _thread_lock.release()


def reconcile(data: dict, rules_shippers_dir: Path) -> bool:
    """강제 종료로 남은 pending 정리. 규칙 파일이 있으면 active, 없으면 abandoned(ID는 계속 예약)."""
    changed = False
    for sid, entry in data["shippers"].items():
        if entry.get("status") == PENDING:
            entry["status"] = ACTIVE if (rules_shippers_dir / f"{sid}.json").exists() else ABANDONED
            changed = True
    return changed
