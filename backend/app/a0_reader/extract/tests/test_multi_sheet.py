"""엑셀 한 파일에 CI·PL·부분품 시트가 같이 있을 때 서류 종류마다 1개씩 (HS 11/26). 가상 샘플만. 담당: KHS"""

from pathlib import Path

from openpyxl import Workbook, load_workbook

from app.a0_reader.extract.service import _sheet_kind, extract_documents

SAMPLE = Path(__file__).resolve().parents[5] / "samples" / "A" / "BL-TEST-003"


def _copy(src: Path, ws) -> None:
    for row in load_workbook(src, data_only=True).active.iter_rows(values_only=True):
        ws.append(list(row))


def test_sheet_kind():
    assert _sheet_kind("CI") == ("CI", False)
    assert _sheet_kind("PL") == ("PL", False)
    assert _sheet_kind("CI SPARE PARTS") == ("CI", True)
    assert _sheet_kind("SPARE PARTS") == ("PL", True)
    assert _sheet_kind("1217 -KOREA") == (None, False)


def test_one_workbook_gives_ci_and_pl(tmp_path):
    wb = Workbook()
    _copy(SAMPLE / "PL.xlsx", wb.active)
    wb.active.title = "PL"
    _copy(SAMPLE / "CI.xlsx", wb.create_sheet("CI"))
    _copy(SAMPLE / "CI.xlsx", wb.create_sheet("CI SPARE PARTS"))
    path = tmp_path / "INV PL.xlsx"
    wb.save(path)

    docs = extract_documents(path, path.name, "A", "f1")
    by = {d.doc_type: d for d in docs}
    assert set(by) == {"CI", "PL"}
    pl_alone = extract_documents(SAMPLE / "PL.xlsx", "PL.xlsx", "A", "f")[0]
    ci_alone = extract_documents(SAMPLE / "CI.xlsx", "CI.xlsx", "A", "f")[0]
    assert len(by["PL"].lines) == len(pl_alone.lines) > 0
    n = len(ci_alone.lines)
    # 부분품 시트가 본품 줄을 그대로 다시 적었으면 두 번 넣지 않는다(HS 11/27 CI 합계 2배 문제)
    assert len(by["CI"].lines) == n
    assert [ln.is_part for ln in by["CI"].lines] == [ln.is_part for ln in ci_alone.lines]


def test_single_sheet_falls_back(tmp_path):
    docs = extract_documents(SAMPLE / "CI.xlsx", "CI.xlsx", "A", "f1")
    assert len(docs) == 1 and docs[0].doc_type == "CI"
