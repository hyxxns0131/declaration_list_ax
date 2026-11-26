"""스캔본·사진 → 화주명을 검은 칸으로 가린 PNG (HS 결정 11/26: "캡쳐본으로, 화주명 먼저 가리고 png로"). 담당: KHS

글자가 없는 이미지는 Windows 기본 OCR(Windows.Media.Ocr, win_ocr.ps1)로 낱말 위치를 찾는다. 새 라이브러리 없음.
- 가릴 이름이 없거나, OCR이 안 되거나, 이름을 한 번도 못 찾으면 None → 그 이미지는 OpenAI로 보내지 않는다.
- OCR 글자는 메모리에서만 쓰고 파일·로그에 남기지 않는다. SAVE_DIR을 정하면(평가 때만) 가린 PNG를 그 폴더에 남긴다.
"""

import json
import re
import subprocess
import sys
import tempfile
import uuid
from io import BytesIO
from pathlib import Path

from app.core.masking import SHORT  # noqa: E402

PS_SCRIPT = Path(__file__).with_name("win_ocr.ps1")
PAD = 4  # 가림 칸 여백(px)
SAVE_DIR: Path | None = None  # 평가 스크립트가 data/ 아래로 정할 때만 예시 PNG를 남긴다

# 이름 끝의 회사 형태 글자는 빼고도 찾는다(OCR이 'CO., LTD.'를 자주 틀림)
_SUFFIX = re.compile(
    r"(주식회사|\(주\)|㈜|CO\.?,?\s*LTD\.?|CO\.?|LTD\.?|INC\.?|CORP\.?|LIMITED)", re.I
)


def _norm(text: str) -> str:
    return re.sub(r"[^0-9A-Z가-힣]", "", text.upper())


def name_keys(names: list[str]) -> list[str]:
    """찾을 이름 조각: 원래 이름 + 회사 형태를 뺀 이름(3글자 이상만)."""
    keys: set[str] = set()
    for n in names:
        for v in (n, _SUFFIX.sub(" ", n)):
            k = _norm(v)
            if len(k) >= 3:
                keys.add(k)
    return sorted(keys, key=len, reverse=True)


def to_png(data: bytes) -> bytes:
    from PIL import Image

    with Image.open(BytesIO(data)) as im:
        buf = BytesIO()
        im.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()


def ocr_lines(png: bytes) -> list[dict] | None:
    """[{text, words:[{text,x,y,w,h}]}]. Windows가 아니거나 실패하면 None."""
    if sys.platform != "win32" or not PS_SCRIPT.exists():
        return None
    tmp = Path(tempfile.gettempdir()) / f"dl_ocr_{uuid.uuid4().hex}.png"
    try:
        tmp.write_bytes(png)
        out = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(PS_SCRIPT),
                "-Path",
                str(tmp),
            ],
            capture_output=True,
            timeout=120,
        )
        if out.returncode != 0:
            return None
        return json.loads(out.stdout.decode("utf-8", errors="replace") or "{}").get("lines") or []
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    finally:
        tmp.unlink(missing_ok=True)


def find_boxes(lines: list[dict], keys: list[str]) -> list[tuple[int, int, int, int]]:
    """줄마다 낱말을 이어 붙여 이름 조각을 찾고, 그 글자 범위에 걸친 낱말 칸을 돌려준다."""
    boxes: list[tuple[int, int, int, int]] = []
    for line in lines:
        words = line.get("words") or []
        joined, spans = "", []
        for w in words:
            t = _norm(str(w.get("text", "")))
            spans.append((len(joined), len(joined) + len(t)))
            joined += t
        for k in keys:
            if len(k) <= SHORT:  # 짧은 약칭은 낱말 하나가 통째로 같을 때만
                for w in words:
                    if _norm(str(w.get("text", ""))) == k:
                        x, y = int(w["x"]), int(w["y"])
                        boxes.append(
                            (x - PAD, y - PAD, x + int(w["w"]) + PAD, y + int(w["h"]) + PAD)
                        )
                continue
            start = joined.find(k)
            while start >= 0:
                end = start + len(k)
                for (a, b), w in zip(spans, words, strict=True):
                    if a < end and b > start:
                        x, y = int(w["x"]), int(w["y"])
                        boxes.append(
                            (x - PAD, y - PAD, x + int(w["w"]) + PAD, y + int(w["h"]) + PAD)
                        )
                start = joined.find(k, end)
    return boxes


def redact_png(image: bytes, names: list[str]) -> bytes | None:
    """화주명을 가린 PNG. 가릴 이름이 없거나 위치를 못 찾으면 None(보내지 않는다)."""
    from PIL import Image, ImageDraw

    keys = name_keys(names)
    if not keys:
        return None
    png = to_png(image)
    lines = ocr_lines(png)
    if not lines:
        return None
    boxes = find_boxes(lines, keys)
    if not boxes:
        return None
    with Image.open(BytesIO(png)) as im:
        im = im.convert("RGB")
        draw = ImageDraw.Draw(im)
        for b in boxes:
            draw.rectangle(b, fill=(0, 0, 0))
        buf = BytesIO()
        im.save(buf, format="PNG")
    out = buf.getvalue()
    if SAVE_DIR is not None:
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        (SAVE_DIR / f"redacted_{uuid.uuid4().hex[:8]}.png").write_bytes(out)
    return out


def redact_pages(images: list[bytes], names: list[str]) -> list[bytes]:
    """이름을 찾아 가린 쪽만 돌려준다(못 찾은 쪽은 빼서 보내지 않는다)."""
    out = []
    for img in images:
        r = redact_png(img, names)
        if r is not None:
            out.append(r)
    return out
