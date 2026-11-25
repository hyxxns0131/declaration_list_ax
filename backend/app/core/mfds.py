"""식약처 공공데이터 API: 해외제조업소(등록 공장), 수입신고 접수 업체. 담당: KHS (A3-3이 사용)

기존 도구 customs/overseas_maker.py와 같은 주소·파라미터(공공데이터포털 1471000).
- 회사명 → 등록 공장 목록(업소코드·주소·시설취소일·취하 여부). 이름이 정확히 같은 것만.
- 결과는 하루 동안 로컬 캐시(api_cache)에 둔다. 키가 없거나 통신 실패면 MfdsError.
인증키는 로그·오류 글에 남기지 않는다.
"""

import re

import httpx

from app.core.config import get_settings
from app.core.storage import work_db_more as store

BASE_URL = "https://apis.data.go.kr/1471000/"
MAKER_PATH = "IprtFoodOvseaMnftBsshInfoService02/getIprtFoodOvseaMnftBsshInfoInq02"
RCPT_PATH = "IprtFoodIprtDclrRcptEntpService01/getIprtFoodIprtDclrRcptEntpInq01"
CACHE_HOURS = 24
MAX_PAGES = 20


class MfdsError(Exception):
    pass


def norm_name(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (name or "").upper())


def _call(path: str, key: str, **params: str) -> list[dict]:
    if not key:
        raise MfdsError("식약처 API 키가 없습니다")
    out: list[dict] = []
    page = 1
    while True:
        try:
            r = httpx.get(
                BASE_URL + path,
                params={
                    "serviceKey": key,
                    "pageNo": page,
                    "numOfRows": 100,
                    "type": "json",
                    **params,
                },
                timeout=60,
            )
            r.raise_for_status()
            d = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise MfdsError(f"식약처 조회 실패({type(e).__name__})") from None
        header = d.get("header") or d.get("response", {}).get("header", {})
        body = d.get("body") or d.get("response", {}).get("body", {})
        if header.get("resultCode") not in ("00", "0", None):
            raise MfdsError(f"식약처 결과코드 {header.get('resultCode')}")
        items = body.get("items") or []
        items = items if isinstance(items, list) else [items]
        out += [i.get("item", i) if isinstance(i, dict) else i for i in items]
        total = int(body.get("totalCount") or 0)
        if page * 100 >= total or not items or page >= MAX_PAGES:
            break
        page += 1
    return out


def factory_status(f: dict) -> str:
    """'정상' 또는 문제 목록(시설 취소·등록 취하·수입중단)."""
    bad = []
    if f.get("FCLT_RTRCN_DT"):
        bad.append(f"시설 취소({f['FCLT_RTRCN_DT']})")
    if (f.get("DSCTN_YN") or "N") == "Y":
        bad.append("등록 취하")
    for k, v in f.items():
        if "STOP" in k.upper() and v:
            bad.append(f"수입중단 정보: {v}")
    return ", ".join(bad) or "정상"


def factories(company: str) -> list[dict]:
    """회사명 → 등록 공장 [{code, name, address, status}] (이름이 정확히 같은 것만)."""
    key = f"maker:{norm_name(company)}"
    hit = store.cache_get(key, CACHE_HOURS)
    if isinstance(hit, list):
        return hit
    rows = _call(MAKER_PATH, get_settings().mfds_overseas_maker_api_key, OCTR_MNFT_BSSH_NM=company)
    out = [
        {
            "code": r.get("OCTR_MNFT_BSSH_CD") or "",
            "name": r.get("OCTR_MNFT_BSSH_NM") or "",
            "address": r.get("OCTR_MNFT_BSSH_ADDR") or "",
            "status": factory_status(r),
        }
        for r in rows
        if norm_name(r.get("OCTR_MNFT_BSSH_NM") or "") == norm_name(company)
    ]
    store.cache_put(key, out)
    return out


def declared_factories(receipt_no: str) -> list[dict]:
    """수입신고 접수번호 → 그 신고에 쓴 해외제조업소(코드·회사명·주소). API는 최근 신고만 준다."""
    key = f"declared:{receipt_no}"
    hit = store.cache_get(key)
    if isinstance(hit, list):
        return hit
    rows = _call(
        RCPT_PATH, get_settings().mfds_import_rcpt_entp_api_key, IPRT_DCLR_RCPT_NO=receipt_no
    )
    out = [
        {
            "code": r.get("OCTR_MNFT_BSSH_CD") or "",
            "name": r.get("OCTR_MNFT_BSSH_NM") or "",
            "address": r.get("OCTR_MNFT_BSSH_ADDR") or "",
        }
        for r in rows
    ]
    if out:
        store.cache_put(key, out)
    return out
