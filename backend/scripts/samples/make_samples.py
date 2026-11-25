"""가상·비식별 선적서류(엑셀) 만들기. 실제 화주·공장·B/L과 무관한 지어낸 값만 쓴다. 담당: KHS

실행: cd backend && python scripts/samples/make_samples.py
결과: samples/<화주>/<B/L 가명>/{CI,PL,BL,CO}.xlsx, samples/unipass/<B/L>.json
"""

import json
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[3] / "samples"

FACTORY_A = (
    "VIRTUAL APPLIANCE FACTORY CO., LTD.",
    "NO. 1 TEST ROAD, SAMPLE DISTRICT, VIRTUAL CITY, CN",
)
FACTORY_B = ("VIRTUAL KITCHENWARE CO., LTD.", "NO. 9 DEMO STREET, MOCK TOWN, VIRTUAL PROVINCE, CN")
EXPORTER = "VIRTUAL TRADING CO., LTD."

# (모델, 품명, 입수, 카톤, 순중량, 총중량, 금액, 색상)
Line = tuple[str, str, int, int, float, float, float, str]

SHIPMENTS: list[dict] = [
    {
        "shipper": "A",
        "folder": "BL-TEST-001",
        "bl": "BLTEST001",
        "invoice": "INV-A-0001",
        "date": "2026-11-10",
        "on_board": "2026-11-12",
        "vessel": "VIRTUAL STAR 101E",
        "currency": "USD",
        "factory": FACTORY_A,
        "docs": ["CI", "PL", "BL", "CO"],
        "lines": [
            ("RC-100", "ELECTRIC RICE COOKER 6 CUP", 1, 12, 96.0, 110.0, 1200.0, ""),
            ("RC-200", "ELECTRIC RICE COOKER 10 CUP", 1, 8, 80.0, 92.0, 1040.0, ""),
            ("RC-100-IP", "INNER POT (SPARE PART)", 10, 2, 14.0, 16.0, 210.0, ""),
            ("RC-100-SP", "STEAM PLATE (SPARE PART)", 20, 1, 5.0, 6.0, 60.0, ""),
        ],
        "unipass": {
            "cargo_no": "26VSTR1010100010000",
            "vessel": "VIRTUAL STAR",
            "arrival_place_code": "03077001",
            "arrival_date": "2026-11-20",
            "entry_date": "2026-11-18",
            "port_of_arrival": "KRPUS",
            "port_of_loading": "CNSHA",
        },
    },
    {
        "shipper": "A",
        "folder": "BL-TEST-002",
        "bl": "BLTEST002",
        "invoice": "INV-A-0002",
        "date": "2026-11-15",
        "on_board": "2026-11-16",
        "vessel": "VIRTUAL OCEAN 202W",
        "currency": "USD",
        "factory": FACTORY_A,
        "docs": ["CI", "PL", "BL"],  # C/O 빠짐 → 제조사 확인 필요
        "lines": [
            ("RC-100", "ELECTRIC RICE COOKER 6 CUP", 1, 10, 80.0, 92.0, 1000.0, ""),
            ("RC-300", "ELECTRIC PRESSURE RICE COOKER", 1, 5, 55.0, 62.0, 900.0, ""),
        ],
        "unipass": {
            "cargo_no": "26VOCN2020200010000",
            "vessel": "VIRTUAL OCEAN",
            "arrival_place_code": "03077001",
            "arrival_date": "",
            "entry_date": "2026-11-24",
            "port_of_arrival": "KRPUS",
            "port_of_loading": "CNNGB",
        },
    },
    {
        "shipper": "B",
        "folder": "BL-TEST-101",
        "bl": "BLTEST101",
        "invoice": "INV-B-0101",
        "date": "2026-11-08",
        "on_board": "2026-11-09",
        "vessel": "VIRTUAL MOON 303E",
        "currency": "USD",
        "factory": FACTORY_B,
        "docs": ["CI", "PL", "BL", "CO"],
        "lines": [
            ("POT-14", "STAINLESS POT 14CM", 6, 5, 30.0, 33.0, 300.0, "SILVER"),
            ("POT-16", "STAINLESS POT 16CM", 6, 5, 33.0, 36.0, 330.0, "SILVER"),
            ("POT-18", "STAINLESS POT 18CM", 6, 5, 36.0, 39.0, 360.0, "SILVER"),
            ("POT-20", "STAINLESS POT 20CM", 4, 5, 32.0, 35.0, 380.0, "SILVER"),
            ("POT-22", "STAINLESS POT 22CM", 4, 5, 35.0, 38.0, 400.0, "SILVER"),
            ("POT-24", "STAINLESS POT 24CM", 4, 5, 38.0, 41.0, 420.0, "SILVER"),
            ("PAN-24", "FRYING PAN 24CM", 10, 4, 28.0, 31.0, 480.0, "BLACK"),
            ("PAN-28", "FRYING PAN 28CM", 10, 4, 34.0, 37.0, 560.0, "BLACK"),
        ],
        "unipass": {
            "cargo_no": "26VMON3030300010000",
            "vessel": "VIRTUAL MOON",
            "arrival_place_code": "02012345",
            "arrival_date": "2026-11-19",
            "entry_date": "2026-11-17",
            "port_of_arrival": "KRINC",
            "port_of_loading": "CNSHA",
        },
    },
]


def _save(wb: Workbook, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def _head(ws, title: str, pairs: list[tuple[str, object]]) -> None:
    ws.append([title])
    ws.append([])
    for k, v in pairs:
        ws.append([k, v])
    ws.append([])


def make_ci(s: dict, path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    _head(
        ws,
        "COMMERCIAL INVOICE",
        [
            ("Seller:", EXPORTER),
            ("Invoice No.:", s["invoice"]),
            ("Date:", s["date"]),
            ("B/L No.:", s["bl"]),
            ("Vessel:", s["vessel"]),
            ("Currency:", s["currency"]),
        ],
    )
    color = any(ln[7] for ln in s["lines"])
    hdr = ["Model", "Description", "Q'ty/CTN", "CTNS", "N.W.(KG)", f"Amount ({s['currency']})"]
    ws.append(hdr + (["Color"] if color else []))
    for m, d, q, c, nw, _gw, amt, col in s["lines"]:
        ws.append([m, d, q, c, nw, amt] + ([col] if color else []))
    ws.append(
        [
            "TOTAL",
            "",
            "",
            sum(ln[3] for ln in s["lines"]),
            sum(ln[4] for ln in s["lines"]),
            sum(ln[6] for ln in s["lines"]),
        ]
    )
    _save(wb, path)


def make_pl(s: dict, path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    _head(
        ws,
        "PACKING LIST",
        [("Invoice No.:", s["invoice"]), ("Date:", s["date"]), ("B/L No.:", s["bl"])],
    )
    ws.append(["Model", "Description", "Q'ty/CTN", "CTNS", "N.W.(KG)", "G.W.(KG)"])
    for m, d, q, c, nw, gw, _amt, _col in s["lines"]:
        ws.append([m, d, q, c, nw, gw])
    ws.append(
        [
            "TOTAL",
            "",
            "",
            sum(ln[3] for ln in s["lines"]),
            sum(ln[4] for ln in s["lines"]),
            sum(ln[5] for ln in s["lines"]),
        ]
    )
    _save(wb, path)


def make_bl(s: dict, path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    _head(
        ws,
        "BILL OF LADING",
        [
            ("B/L No.:", s["bl"]),
            ("Shipper:", EXPORTER),
            ("Vessel / Voyage:", s["vessel"]),
            ("Port of Loading:", s["unipass"]["port_of_loading"]),
            ("Port of Discharge:", s["unipass"]["port_of_arrival"]),
            ("Shipped on Board Date:", s["on_board"]),
            ("Number of Packages:", sum(ln[3] for ln in s["lines"])),
            ("Gross Weight (KG):", sum(ln[5] for ln in s["lines"])),
        ],
    )
    _save(wb, path)


def make_co(s: dict, path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    _head(
        ws,
        "CERTIFICATE OF ORIGIN",
        [
            ("Exporter:", EXPORTER),
            ("Producer:", s["factory"][0]),
            ("Producer Address:", s["factory"][1]),
            ("B/L No.:", s["bl"]),
            ("Country of Origin:", "CHINA"),
        ],
    )
    _save(wb, path)


MAKERS = {"CI": make_ci, "PL": make_pl, "BL": make_bl, "CO": make_co}


def main() -> None:
    for s in SHIPMENTS:
        folder = ROOT / s["shipper"] / s["folder"]
        for d in s["docs"]:
            MAKERS[d](s, folder / f"{d}.xlsx")
        up = ROOT / "unipass" / f"{s['bl']}.json"
        up.parent.mkdir(parents=True, exist_ok=True)
        up.write_text(
            json.dumps({"bl_no": s["bl"], **s["unipass"]}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("made", folder.relative_to(ROOT))


if __name__ == "__main__":
    main()
