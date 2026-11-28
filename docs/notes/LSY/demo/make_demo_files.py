"""시연용 가상 서류 만들기 (B사 그릇, 내색·외색). 담당: LSY

모든 값은 가상(VIRTUAL·DEMO)이다. 실제 화주·공장·실적과 관계없다.
만드는 것 (이미 있으면 덮어씀, 다른 파일은 건드리지 않음):
- samples/B/BL-DEMO-201/{CI,PL,BL,CO}.xlsx   B사 도자기 그릇 선적서류 1건
- samples/unipass/BLDEMO201.json             유니패스 가짜 응답(UNIPASS_MODE=mock)
- samples/mfds/demo_lsy.json                 가상 등록 공장(서류 표기와 공백만 다름)
- docs/notes/LSY/demo/registry/B/*.json      탭 2 등록용 수입신고서·시험성적서(가상)
실행: cd backend && python ../docs/notes/LSY/demo/make_demo_files.py
"""

import json
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[4]
BL = "BLDEMO201"
VESSEL = "VIRTUAL SUN 505E"
PRODUCER = "VIRTUAL HAN SEONG CERAMICS CO., LTD."  # 등록 이름은 HANSEONG(공백 차이 시연)
ADDRESS = "NO. 5 CLAY ROAD, KILN TOWN, VIRTUAL PROVINCE, CN"
SELLER = "VIRTUAL TRADING CO., LTD."
# 모델, 품명, 카톤당, 카톤, 순중량, 금액, 내색, 외색
LINES = [
    ("BWL-W15", "CERAMIC BOWL 15CM WHITE", 24, 6, 31, 240, "WHITE", "BLUE"),
    ("BWL-B15", "CERAMIC BOWL 15CM BLUE", 24, 4, 21, 160, "BLUE", "BLUE"),
    ("BWL-W18", "CERAMIC BOWL 18CM WHITE", 12, 5, 28, 210, "WHITE", "WHITE"),
]


def _save(path: Path, rows: list[list]) -> None:
    wb = Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def docs() -> None:
    d = ROOT / "samples" / "B" / "BL-DEMO-201"
    ctns = sum(x[3] for x in LINES)
    nw = sum(x[4] for x in LINES)
    gw = nw + 3 * len(LINES)
    head = [["Invoice No.:", "INV-B-DEMO-201"], ["Date:", "2026-11-18"], ["B/L No.:", BL]]
    _save(
        d / "CI.xlsx",
        [
            ["COMMERCIAL INVOICE"],
            ["Seller:", SELLER],
            *head,
            ["Vessel:", VESSEL],
            ["Currency:", "USD"],
            [
                "Model",
                "Description",
                "Q'ty/CTN",
                "CTNS",
                "N.W.(KG)",
                "Amount (USD)",
                "Inner Color",
                "Outer Color",
            ],
            *[list(x) for x in LINES],
            ["TOTAL", None, None, ctns, nw, sum(x[5] for x in LINES)],
        ],
    )
    _save(
        d / "PL.xlsx",
        [
            ["PACKING LIST"],
            *head,
            ["Model", "Description", "Q'ty/CTN", "CTNS", "N.W.(KG)", "G.W.(KG)"],
            *[[m, ds, q, c, n, n + 3] for m, ds, q, c, n, *_ in LINES],
            ["TOTAL", None, None, ctns, nw, gw],
        ],
    )
    _save(
        d / "BL.xlsx",
        [
            ["BILL OF LADING"],
            ["B/L No.:", BL],
            ["Shipper:", SELLER],
            ["Vessel / Voyage:", VESSEL],
            ["Port of Loading:", "CNSHA"],
            ["Port of Discharge:", "KRPUS"],
            ["Shipped on Board Date:", "2026-11-20"],
            ["Number of Packages:", ctns],
            ["Gross Weight (KG):", gw],
        ],
    )
    _save(
        d / "CO.xlsx",
        [
            ["CERTIFICATE OF ORIGIN"],
            ["Exporter:", SELLER],
            ["Producer:", PRODUCER],
            ["Producer Address:", ADDRESS],
            ["B/L No.:", BL],
            ["Country of Origin:", "CHINA"],
        ],
    )


def write_json(path: Path, body) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mocks() -> None:
    write_json(
        ROOT / "samples" / "unipass" / f"{BL}.json",
        {
            "bl_no": BL,
            "cargo_no": "26VSUN5050500010000",
            "vessel": "VIRTUAL SUN",
            "arrival_place_code": "03012345",
            "arrival_date": "2026-11-27",
            "entry_date": "2026-11-26",
            "port_of_arrival": "KRPUS",
            "port_of_loading": "CNSHA",
        },
    )
    write_json(
        ROOT / "samples" / "mfds" / "demo_lsy.json",
        [
            {
                "code": "CN900000201",
                "name": "VIRTUAL HANSEONG CERAMICS CO., LTD.",
                "address": ADDRESS,
                "status": "정상",
            },
        ],
    )


def registry() -> None:
    """실적 3건: W15용 2건(같은 재질 → 최신 승인일 선택), B15용 1건(내색 BLUE). W18은 실적 없음."""
    d = Path(__file__).resolve().parent / "registry" / "B"
    # 재질 코드(14자리)는 지어내지 않는다: 코드 칸은 비움 → 확인 필요
    mat = [{"code": "", "name": "도자기제"}]
    recs = [
        ("202500000201", "2025-05-10", "2025-05-24", "BWL-W15", "WHITE"),
        ("202500000205", "2025-07-01", "2025-07-13", "BWL-W15", "WHITE"),
        ("202500000202", "2025-05-10", "2025-05-24", "BWL-B15", "BLUE"),
    ]
    for no, rcv, ok, model, color in recs:
        write_json(
            d / f"{no} {model} 수입신고서.json",
            {
                "kind": "수입신고서",
                "model": model,
                "data": {
                    "receipt_no": no,
                    "receipt_date": rcv,
                    "accepted_date": ok,
                    "inspection_type": "정밀",
                    "product_en": f"CERAMIC BOWL({model})",
                    "product_ko": f"도자기 그릇({model})",
                    "materials": mat,
                    "maker_code": "CN900000201",
                    "maker_name": "VIRTUAL HANSEONG CERAMICS CO., LTD.",
                    "maker_address": ADDRESS,
                },
            },
        )
        write_json(
            d / f"{no} 시험성적서.json",
            {
                "kind": "시험성적서",
                "data": {
                    "receipt_no": no,
                    "approval_date": ok,
                    "samples": [
                        {"material": "도자기", "part": "그릇 본체", "color": color, "remark": ""}
                    ],
                    "models": [model],
                },
            },
        )


if __name__ == "__main__":
    docs()
    mocks()
    registry()
    print(
        "가상 서류를 만들었습니다: samples/B/BL-DEMO-201, samples/unipass, samples/mfds, docs/notes/LSY/demo/registry/B"
    )
