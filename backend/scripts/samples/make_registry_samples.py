"""가상·비식별 실적 자료 만들기: 수입신고서·시험성적서 판독 JSON, 식약처 가상 공장, 가상 관세환율. 담당: KHS

실제 화주·공장·실적과 무관한 지어낸 값만 쓴다. 재질명은 식약처 재질 코드명(공개 자료)을 쓴다.
실행: cd backend && python scripts/samples/make_registry_samples.py
결과: samples/registry/<화주>/*.json, samples/mfds/factories.json, samples/unipass/fx.json
JSON 형식은 기존 도구 수입신고서.json / test_reports/<번호>.json과 같다.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "samples"

FACTORY_A = (
    "VIRTUAL APPLIANCE FACTORY CO., LTD.",
    "NO. 1 TEST ROAD, SAMPLE DISTRICT, VIRTUAL CITY, CN",
)
FACTORY_A2 = "NO. 77 OTHER ROAD, ELSEWHERE TOWN, VIRTUAL CITY, CN"  # 같은 회사 다른 공장
FACTORY_B = ("VIRTUAL KITCHENWARE CO., LTD.", "NO. 9 DEMO STREET, MOCK TOWN, VIRTUAL PROVINCE, CN")

FACTORIES = [
    {"code": "CN900000001", "name": FACTORY_A[0], "address": FACTORY_A[1], "status": "정상"},
    {"code": "CN900000002", "name": FACTORY_A[0], "address": FACTORY_A2, "status": "정상"},
    {"code": "CN900000101", "name": FACTORY_B[0], "address": FACTORY_B[1], "status": "정상"},
]

FX = {
    "USD": {"rate": 1380.0, "unit": 1, "from": "20261122"},
    "CNY": {"rate": 190.0, "unit": 1, "from": "20261122"},
    "JPY": {"rate": 9.2, "unit": 1, "from": "20261122"},
    "EUR": {"rate": 1500.0, "unit": 1, "from": "20261122"},
}


def decl(receipt, date, accepted, kind, en, ko, mats, factory, code):
    return {
        "kind": "수입신고서",
        "model": en.split("(")[-1].rstrip(")"),
        "data": {
            "receipt_no": receipt,
            "receipt_date": date,
            "accepted_date": accepted,
            "inspection_type": kind,
            "product_en": en,
            "product_ko": ko,
            "materials": [{"code": c, "name": n} for n, c in mats],
            "maker_code": code,
            "maker_name": factory[0],
            "maker_address": factory[1],
        },
    }


def report(receipt, approved, samples, models):
    return {
        "kind": "시험성적서",
        "data": {
            "receipt_no": receipt,
            "approval_date": approved,
            "samples": [
                {"material": m, "part": p, "color": c, "remark": ""} for m, p, c in samples
            ],
            "models": models,
        },
    }


# (재질 코드명, 14자리 코드 — 가상 코드, 실제 코드표는 Supabase material_codes)
FLUORO = ("금속제(불소수지도장)", "D5000002B20000")
PP = ("폴리프로필렌", "D1000003000000")
STS = ("스테인레스", "D5000003000000")

SAMPLES: dict[str, dict[str, dict]] = {
    "A": {
        # 정밀검사 → 실적 202300000101 (유효, 2028-04-25 만료)
        "RC-100 수입신고서.json": decl(
            "202300000101",
            "2023-04-10",
            "2023-04-25",
            "정밀",
            "ELECTRIC RICE COOKER(RC-100)",
            "전기밥솥(RC-100)",
            [FLUORO, PP],
            FACTORY_A,
            "CN900000001",
        ),
        "202300000101 시험성적서.json": report(
            "202300000101",
            "2023-04-25",
            [(FLUORO[0], "내솥", "검정"), (PP[0], "뚜껑", "흰색")],
            ["RC-100"],
        ),
        # 서류검사 → 실적 202300000101을 썼던 모델(같은 공장·같은 품명·재질 포함)
        "RC-200 수입신고서.json": decl(
            "202500000202",
            "2025-02-03",
            "2025-02-05",
            "서류",
            "ELECTRIC RICE COOKER(RC-200)",
            "전기밥솥(RC-200)",
            [FLUORO, PP],
            FACTORY_A,
            "CN900000001",
        ),
        # 정밀검사 → 실적 202100000303 (2026-12-20 만료 → 1개월 안 알림)
        "RC-300 수입신고서.json": decl(
            "202100000303",
            "2021-12-01",
            "2021-12-20",
            "정밀",
            "ELECTRIC PRESSURE RICE COOKER(RC-300)",
            "전기압력밥솥(RC-300)",
            [STS, PP],
            FACTORY_A,
            "CN900000001",
        ),
        # 오래된 정밀검사 → 만료 실적(취소선 표시)
        "RC-100 옛 수입신고서.json": decl(
            "202000000404",
            "2020-05-20",
            "2020-06-01",
            "정밀",
            "ELECTRIC RICE COOKER(RC-100)",
            "전기밥솥(RC-100)",
            [FLUORO],
            FACTORY_A,
            "CN900000001",
        ),
    },
    "B": {
        "POT-14 수입신고서.json": decl(
            "202400000501",
            "2024-03-02",
            "2024-03-15",
            "정밀",
            "STAINLESS POT(POT-14)",
            "스테인레스 냄비(POT-14)",
            [STS],
            FACTORY_B,
            "CN900000101",
        ),
        "202400000501 시험성적서.json": report(
            "202400000501",
            "2024-03-15",
            [(STS[0], "몸체", "SILVER")],
            ["POT-14"],
        ),
        "PAN-24 수입신고서.json": decl(
            "202400000602",
            "2024-05-02",
            "2024-05-20",
            "정밀",
            "FRYING PAN(PAN-24)",
            "프라이팬(PAN-24)",
            [FLUORO],
            FACTORY_B,
            "CN900000101",
        ),
        "202400000602 시험성적서.json": report(
            "202400000602",
            "2024-05-20",
            [(FLUORO[0], "몸체", "BLACK")],
            ["PAN-24"],
        ),
    },
}


def main() -> None:
    for shipper, files in SAMPLES.items():
        folder = ROOT / "registry" / shipper
        folder.mkdir(parents=True, exist_ok=True)
        for name, body in files.items():
            (folder / name).write_text(
                json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    (ROOT / "mfds").mkdir(parents=True, exist_ok=True)
    (ROOT / "mfds" / "factories.json").write_text(
        json.dumps(FACTORIES, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ROOT / "unipass" / "fx.json").write_text(json.dumps(FX, indent=2), encoding="utf-8")
    print("samples/registry, samples/mfds, samples/unipass/fx.json 생성")


if __name__ == "__main__":
    main()
