"""유니패스 조회 진입점: 화물진행정보(반입·입항), 검사검역내역(실적 승인일). 담당: KHS [재사용] A1-6

- UNIPASS_MODE=live: 관세청 OPEN API를 부른다(기존 도구 common/unipass_client.py와 같은 주소·파라미터).
  live에서 못 찾았고 samples/unipass/<B/L>.json(가상 자료)이 있으면 그것을 쓴다 → 시연용 가상 B/L.
- UNIPASS_MODE=mock: samples/unipass/*.json만.
- 신청서 작성·전송 코드는 만들지 않는다(AGENTS 0-4, RULES 11-3).
- 인증키는 로그·오류 글에 남기지 않는다.
"""

import re
import xml.etree.ElementTree as ET
from datetime import date

import httpx
from pydantic import BaseModel
from pydantic import Field as PField

from app.core.config import get_settings
from app.core.storage import work_db_more as cache
from app.core.unipass import mock

BASE = "https://unipass.customs.go.kr:38010/ext/rest"
CARGO_URL = f"{BASE}/cargCsclPrgsInfoQry/retrieveCargCsclPrgsInfo"
INSPECTION_URL = f"{BASE}/xtrnUserInscQuanBrkdQry/retrieveXtrnUserInscQuanBrkd"
MFDS_AGENCY = "11"  # 검사검역기관: 식품의약품안전처
CARGO_CACHE_HOURS = 1  # 같은 B/L을 1시간 안에 다시 부르지 않는다
INSPECTION_KEYWORDS = (
    ("검색기", "검색기"),
    ("X-RAY", "검색기"),
    ("XRAY", "검색기"),
    ("개장", "개장검사"),
    ("전량", "전량검사"),
    ("발췌", "발췌검사"),
)


class CargoInfo(BaseModel):
    bl_no: str
    cargo_no: str = ""  # 화물관리번호
    vessel: str = ""  # 모선명(유니패스 기준)
    arrival_place_code: str = ""  # 최종 반입지 장치장 코드
    arrival_place_name: str = ""
    arrival_date: str = ""  # 최종 반입일 YYYY-MM-DD (최종 반입 전이면 빈칸)
    entry_date: str = ""  # 입항일
    entry_reported: bool = False  # '입항보고 수리'가 있으면 입항일 확정
    port_of_arrival: str = ""  # 도착항 코드
    port_of_loading: str = ""  # 선적항 코드
    status: str = ""  # 통관진행상태
    managed_cargo: str = ""  # 관리대상화물 표시(비고용)
    total_packages: str = ""
    total_weight: str = ""
    arrival_packages: str = ""  # 최종 장치장 반입신고 수량·중량 (B/L 대조용)
    arrival_weight: str = ""
    source: str = "mock"  # live | mock
    events: list[dict] = PField(default_factory=list)


class UnipassError(Exception):
    pass


def _date(raw: str) -> str:
    d = re.sub(r"\D", "", raw or "")
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}" if len(d) >= 8 else ""


def _get(url: str, params: dict) -> ET.Element:
    try:
        r = httpx.get(url, params=params, timeout=get_settings().unipass_timeout_sec)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except (httpx.HTTPError, ET.ParseError) as e:
        raise UnipassError(f"유니패스 조회 실패({type(e).__name__})") from None
    msg = (root.findtext(".//ntceInfo") or "").strip()
    if msg and re.search(r"인증|crky|키", msg):
        raise UnipassError("유니패스 인증 오류: 인증키 확인 필요")
    return root


def _gv(el: ET.Element, tag: str) -> str:
    f = el.find(f".//{tag}")
    return f.text.strip() if f is not None and f.text else ""


def resolve_arrival(events: list[dict]) -> dict:
    """최종 반입지·반입일 (기존 도구 resolve_arrival, RULES 11-3). 순수 함수.

    최종 반입지 = '입항적재화물목록' 기록의 마지막 장치장, 반입일 = 그 장치장에 처음 반입신고된 날.
    """
    evs = sorted(events, key=lambda e: e.get("prcsDttm") or "")
    manifest = [e for e in evs if "적재화물목록" in e.get("type", "") and e.get("shedSgn")]
    final_sgn = manifest[-1]["shedSgn"] if manifest else ""
    final_nm = manifest[-1].get("shedNm", "") if manifest else ""
    arrivals = [e for e in evs if "반입신고" in e.get("type", "") and e.get("shedSgn")]
    if not final_sgn and arrivals:
        final_sgn, final_nm = arrivals[0]["shedSgn"], arrivals[0].get("shedNm", "")
    at_final = [e for e in arrivals if e["shedSgn"] == final_sgn]
    first = at_final[0] if at_final else None
    methods: list[str] = []
    for e in evs:
        text = " ".join(str(e.get(k) or "") for k in ("type", "rlbrCn", "guide")).upper()
        for kw, name in INSPECTION_KEYWORDS:
            if kw in text and name not in methods:
                methods.append(name)
    reported = any("입항보고" in e.get("type", "") and "수리" in e.get("type", "") for e in evs)
    return {
        "shed_sgn": final_sgn,
        "shed_nm": final_nm,
        "arrival_date": _date(first.get("rlbrDttm") or first.get("prcsDttm") or "")
        if first
        else "",
        "methods": methods,
        "reported": reported,
        "pck": (first or {}).get("pck", ""),
        "wght": (first or {}).get("wght", ""),
    }


def parse_cargo(root: ET.Element, bl_no: str) -> CargoInfo | None:
    if (_gv(root, "tCnt") or "0") in ("", "0"):
        return None
    vo = root.find(".//cargCsclPrgsInfoQryVo")
    vo = vo if vo is not None else root
    events = [
        {
            "type": _gv(d, "cargTrcnRelaBsopTpcd"),
            "shedSgn": _gv(d, "shedSgn"),
            "shedNm": _gv(d, "shedNm"),
            "rlbrDttm": _gv(d, "rlbrDttm"),
            "prcsDttm": _gv(d, "prcsDttm"),
            "rlbrCn": _gv(d, "rlbrCn"),
            "guide": _gv(d, "bfhnGdncCn"),
            "pck": _gv(d, "pckGcnt"),
            "wght": _gv(d, "wght"),
        }
        for d in root.findall(".//cargCsclPrgsInfoDtlQryVo")
    ]
    arr = resolve_arrival(events)
    managed = _gv(vo, "mtTrgtCargYnNm").upper()
    managed_text = ""
    if managed and managed not in ("N", "NO", "아니오"):
        managed_text = "관리대상화물: " + (", ".join(arr["methods"]) or "검사방식 미확인")
    cargo_no = re.sub(r"[^0-9A-Za-z]", "", _gv(vo, "cargMtNo")).upper()
    return CargoInfo(
        bl_no=bl_no,
        cargo_no=cargo_no,
        vessel=_gv(vo, "shipNm"),
        arrival_place_code=arr["shed_sgn"],
        arrival_place_name=arr["shed_nm"],
        arrival_date=arr["arrival_date"],
        entry_date=_date(_gv(vo, "etprDt")),
        entry_reported=arr["reported"],
        port_of_arrival=_gv(vo, "dsprCd"),
        port_of_loading=_gv(vo, "ldprCd"),
        status=_gv(vo, "csclPrgsStts"),
        managed_cargo=managed_text,
        total_packages=_gv(vo, "pckGcnt"),
        total_weight=_gv(vo, "ttwg"),
        arrival_packages=arr["pck"],
        arrival_weight=arr["wght"],
        source="live",
        events=events,
    )


def _live_cargo(bl_no: str) -> CargoInfo | None:
    key = get_settings().unipass_cargo_api_key
    if not key:
        raise UnipassError("UNIPASS_CARGO_API_KEY가 없습니다")
    year = date.today().year
    for y in (year, year - 1, year - 2):  # 최근 3개년, H B/L → M B/L (기존 도구)
        for field in ("hblNo", "mblNo"):
            root = _get(CARGO_URL, {"crkyCn": key, field: bl_no, "blYy": str(y)})
            msg = (root.findtext(".//ntceInfo") or "").strip()
            if msg.startswith("[N00]"):  # 여러 건 → 대표 화물관리번호로 다시
                first = root.findtext(".//cargMtNo")
                if first:
                    root = _get(CARGO_URL, {"crkyCn": key, "cargMtNo": first})
            got = parse_cargo(root, bl_no)
            if got:
                return got
    return None


def get_cargo(bl_no: str, use_cache: bool = True) -> CargoInfo | None:
    """B/L 번호로 화물 진행 정보. 못 찾으면 None. 통신 실패도 None(행에 '유니패스 조회 실패' 메모)."""
    bl_no = re.sub(r"\s", "", bl_no or "")
    if not bl_no:
        return None
    key = f"cargo:{bl_no}"
    if use_cache:
        hit = cache.cache_get(key, CARGO_CACHE_HOURS)
        if isinstance(hit, dict):
            return CargoInfo.model_validate(hit)
    got: CargoInfo | None = None
    if get_settings().unipass_mode == "live":
        try:
            got = _live_cargo(bl_no)
        except UnipassError:
            got = None
    if got is None:
        data = mock.cargo(bl_no)
        got = CargoInfo.model_validate({**data, "source": "mock"}) if data else None
    if got:
        cache.cache_put(key, got.model_dump())
    return got


def notice_candidates(receipt_no: str, prefixes: list[str]) -> list[str]:
    """접수번호 → 통지번호 후보(기존 도구 inspection.find_notice 규칙). 순수 함수.

    통지번호 = 앞 3글자 + 접수연도 4자리 + 숫자 1자 + 접수번호 뒤 8자리. 앞 글자·숫자는 정해진 규칙이 없어
    이미 찾은 앞 글자부터 차례로 본다.
    """
    if not re.fullmatch(r"\d{12}", receipt_no or ""):
        return []
    year, tail = receipt_no[:4], receipt_no[4:]
    out: list[str] = []
    for pre in prefixes:
        for d in "1370245689":
            no = f"{pre}{year}{d}{tail}"
            if no not in out:
                out.append(no)
    return out


def find_approval(receipt_no: str, prefixes: list[str], max_calls: int = 40) -> dict | None:
    """실적 접수번호 → {ntfc, applied, approved, result, models}. live 모드에서만. 못 찾으면 None."""
    s = get_settings()
    if s.unipass_mode != "live" or not s.unipass_inspection_api_key:
        return None
    hit = cache.cache_get(f"inspection:{receipt_no}")
    if isinstance(hit, dict):
        return hit
    for no in notice_candidates(receipt_no, prefixes)[:max_calls]:
        try:
            root = _get(
                INSPECTION_URL,
                {
                    "crkyCn": s.unipass_inspection_api_key,
                    "inscQuanItt": MFDS_AGENCY,
                    "ntfcNo": no,
                    "dgcnt": "01",
                },
            )
        except UnipassError:
            return None
        if (_gv(root, "tCnt") or "0") in ("", "0"):
            continue
        # 태그 이름: 기존 도구 inspection.py (2026-11-06 확인)
        out = {
            "ntfc": no,
            "applied": _date(_gv(root, "rqstDt")),
            "approved": _date(_gv(root, "inscQuanDtrmDt")),  # 검사/검역 결정일 = 승인일
            "result": _gv(root, "inscQuanPsxaYn"),
            "office": _gv(root, "inscQuanIttNm"),
            "models": [_gv(root, "prnmStsz")] if _gv(root, "prnmStsz") else [],
        }
        cache.cache_put(f"inspection:{receipt_no}", out)
        return out
    return None
