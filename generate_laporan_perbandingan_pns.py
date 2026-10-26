#!/usr/bin/env python3
"""Normalize the August HTML table and compare it with the April JSON snapshot.

This script intentionally uses only Python's standard library so it can run in
the project's current environment without adding dependencies.
"""

from __future__ import annotations

import json
import re
import unicodedata
import zipfile
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from xml.sax.saxutils import escape


BASE_DIR = Path(__file__).resolve().parent
RAW_AUGUST_PATH = BASE_DIR / "datamentah.txt"
APRIL_JSON_PATH = BASE_DIR / "DUKPNSFULLapril.json"
AUGUST_JSON_PATH = BASE_DIR / "datapnsagustus.json"
REPORT_PATH = BASE_DIR / "laporan_perbandingan_PNS_April_vs_Agustus.xlsx"

MONTHS = {
    "JANUARI": "01",
    "FEBRUARI": "02",
    "MARET": "03",
    "APRIL": "04",
    "MEI": "05",
    "JUNI": "06",
    "JULI": "07",
    "AGUSTUS": "08",
    "SEPTEMBER": "09",
    "OKTOBER": "10",
    "NOVEMBER": "11",
    "DESEMBER": "12",
}

FIELD_LABELS = {
    "nama": "Nama/Gelar",
    "status": "Status/Kedudukan",
    "ttl": "Tempat/Tanggal Lahir",
    "golongan": "Pangkat/Golongan",
    "jabatan": "Jabatan",
    "skpd": "SKPD",
    "pendidikan": "Pendidikan Terakhir",
}


class EmployeeTableParser(HTMLParser):
    """Small, purpose-built parser for the HTML table stored in datamentah.txt."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_tbody = False
        self.in_row = False
        self.in_cell = False
        self.rows: list[list[str]] = []
        self.current_row: list[str] = []
        self.current_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "tbody":
            self.in_tbody = True
        elif self.in_tbody and tag == "tr":
            self.in_row = True
            self.current_row = []
        elif self.in_row and tag == "td":
            self.in_cell = True
            self.current_parts = []
        elif self.in_cell and tag == "br":
            self.current_parts.append("\n")
        elif self.in_cell and tag == "img":
            onclick = attributes.get("onclick")
            if onclick:
                self.current_parts.append(f" [[ONCLICK:{onclick}]] ")

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.current_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self.in_cell:
            text = "".join(self.current_parts)
            lines = [re.sub(r"[ \t\r\f\v]+", " ", part).strip() for part in text.split("\n")]
            text = re.sub(r"\n+", "\n", "\n".join(lines)).strip()
            self.current_row.append(text)
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            self.rows.append(self.current_row)
            self.in_row = False
        elif tag == "tbody":
            self.in_tbody = False


def only_digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_for_comparison(value: Any) -> str:
    """Ignore capitalization, accents, spacing, and punctuation during comparison."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").upper()
    return re.sub(r"[^A-Z0-9]+", "", text)


def parse_birth(raw_value: str) -> tuple[str, str, str]:
    """Return place, ISO-like date, and a clean display value."""
    normalized = raw_value.replace("\r", "").strip()
    if "," in normalized:
        place, raw_date = normalized.split(",", 1)
    else:
        place, raw_date = normalized, ""
    place = clean_text(place)
    raw_date = clean_text(raw_date.replace("\n", " "))

    match = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", raw_date)
    if match and match.group(2).upper() in MONTHS:
        day, month_name, year = match.groups()
        iso_date = f"{year}-{MONTHS[month_name.upper()]}-{int(day):02d}"
    elif normalize_for_comparison(raw_date) in {"000000", "0000"}:
        iso_date = "0000-00-00"
    else:
        iso_date = ""

    display = place
    if raw_date:
        display = f"{place},\n{raw_date}"
    return place, iso_date, display


def parse_status(raw_value: str) -> tuple[str, str]:
    parts = [clean_text(part) for part in raw_value.split("/", 1)]
    return parts[0], parts[1] if len(parts) == 2 else ""


def parse_august_data(path: Path) -> list[dict[str, Any]]:
    parser = EmployeeTableParser()
    parser.feed(path.read_text(encoding="utf-8"))

    if not parser.rows:
        raise ValueError("Tidak ada baris pegawai yang ditemukan pada datamentah.txt")

    employees: list[dict[str, Any]] = []
    for row_index, cells in enumerate(parser.rows, start=1):
        if len(cells) != 10:
            raise ValueError(f"Baris HTML ke-{row_index} memiliki {len(cells)} kolom, seharusnya 10")

        status, position = parse_status(cells[3])
        birth_place, birth_date, birth_display = parse_birth(cells[4])
        id_match = re.search(r"lanjut\((\d+),", cells[9])
        employee_id = id_match.group(1) if id_match else ""

        employees.append(
            {
                "no": int(cells[0]),
                "idPegawai": employee_id,
                "nip": only_digits(cells[2]),
                "namaWithGelar": clean_text(cells[1]),
                "statusKepegawaian": status,
                "kedudukanKepegawaian": position,
                "kedudukan": f"{status} / {position}".strip(" /"),
                "tempatLahir": birth_place,
                "tanggalLahir": birth_date,
                "tempatTglLahir": birth_display,
                "golonganTerakhir": clean_text(cells[5]).upper(),
                "jabatanTerakhir": clean_text(cells[6]),
                "skpd": clean_text(cells[7]),
                "pendidikanTerakhir": clean_text(cells[8]),
            }
        )

    expected_numbers = list(range(1, len(employees) + 1))
    actual_numbers = [employee["no"] for employee in employees]
    if actual_numbers != expected_numbers:
        raise ValueError("Nomor urut Agustus tidak berurutan mulai dari 1")

    nips = [employee["nip"] for employee in employees]
    empty_nips = sum(not nip for nip in nips)
    duplicate_nips = {nip: count for nip, count in Counter(nips).items() if nip and count > 1}
    if empty_nips or duplicate_nips:
        raise ValueError(f"NIP Agustus bermasalah: kosong={empty_nips}, duplikat={duplicate_nips}")

    return employees


def latest_education(employee: dict[str, Any]) -> str:
    history = employee.get("riwayatPendidikan")
    if isinstance(history, list) and history:
        latest = history[-1]
        if isinstance(latest, dict):
            return clean_text(latest.get("detailPendidikan") or latest.get("tingkatPendidikan"))
    return clean_text(employee.get("pendidikanTerakhir"))


def april_view(employee: dict[str, Any]) -> dict[str, Any]:
    return {
        "no": "",
        "nip": only_digits(employee.get("nip")),
        "nama": clean_text(employee.get("namaWithGelar") or employee.get("nama")),
        "status": clean_text(employee.get("statusKepegawaian")),
        "kedudukan": clean_text(employee.get("kedudukanKepegawaian")),
        "tempat": clean_text(employee.get("tempatLahir")),
        "tanggal": clean_text(employee.get("tanggalLahir")),
        "ttl": clean_text(employee.get("tempatTglLahir")).replace("\n", ", "),
        "golongan": clean_text(employee.get("golonganTerakhir")),
        "jabatan": clean_text(employee.get("jabatanTerakhir")),
        "skpd": clean_text(employee.get("skpd")),
        "pendidikan": latest_education(employee),
    }


def august_view(employee: dict[str, Any]) -> dict[str, Any]:
    return {
        "no": employee.get("no", ""),
        "nip": only_digits(employee.get("nip")),
        "nama": clean_text(employee.get("namaWithGelar")),
        "status": clean_text(employee.get("statusKepegawaian")),
        "kedudukan": clean_text(employee.get("kedudukanKepegawaian")),
        "tempat": clean_text(employee.get("tempatLahir")),
        "tanggal": clean_text(employee.get("tanggalLahir")),
        "ttl": clean_text(employee.get("tempatTglLahir")).replace("\n", ", "),
        "golongan": clean_text(employee.get("golonganTerakhir")),
        "jabatan": clean_text(employee.get("jabatanTerakhir")),
        "skpd": clean_text(employee.get("skpd")),
        "pendidikan": clean_text(employee.get("pendidikanTerakhir")),
    }


def changed_fields(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    changes: list[str] = []
    if normalize_for_comparison(old["nama"]) != normalize_for_comparison(new["nama"]):
        changes.append("nama")
    if (
        normalize_for_comparison(old["status"]) != normalize_for_comparison(new["status"])
        or normalize_for_comparison(old["kedudukan"]) != normalize_for_comparison(new["kedudukan"])
    ):
        changes.append("status")
    if (
        normalize_for_comparison(old["tempat"]) != normalize_for_comparison(new["tempat"])
        or normalize_for_comparison(old["tanggal"]) != normalize_for_comparison(new["tanggal"])
    ):
        changes.append("ttl")
    for field in ("golongan", "jabatan", "skpd", "pendidikan"):
        if normalize_for_comparison(old[field]) != normalize_for_comparison(new[field]):
            changes.append(field)
    return changes


REPORT_HEADERS = [
    "No. Laporan",
    "No. Agustus",
    "Status Perbandingan",
    "Bidang Berubah",
    "NIP",
    "Nama/Gelar April",
    "Nama/Gelar Agustus",
    "Status/Kedudukan April",
    "Status/Kedudukan Agustus",
    "TTL April",
    "TTL Agustus",
    "Pangkat/Gol. April",
    "Pangkat/Gol. Agustus",
    "Jabatan April",
    "Jabatan Agustus",
    "SKPD April",
    "SKPD Agustus",
    "Pendidikan April",
    "Pendidikan Agustus",
]


def report_row(
    sequence: int,
    status: str,
    change_codes: list[str],
    old: dict[str, Any] | None,
    new: dict[str, Any] | None,
) -> list[Any]:
    old = old or {key: "" for key in ("nama", "status", "kedudukan", "ttl", "golongan", "jabatan", "skpd", "pendidikan")}
    new = new or {key: "" for key in ("no", "nama", "status", "kedudukan", "ttl", "golongan", "jabatan", "skpd", "pendidikan")}
    nip = new.get("nip") or old.get("nip") or ""
    change_labels = ", ".join(FIELD_LABELS[code] for code in change_codes)
    return [
        sequence,
        new.get("no", ""),
        status,
        change_labels,
        nip,
        old.get("nama", ""),
        new.get("nama", ""),
        " / ".join(part for part in (old.get("status", ""), old.get("kedudukan", "")) if part),
        " / ".join(part for part in (new.get("status", ""), new.get("kedudukan", "")) if part),
        old.get("ttl", ""),
        new.get("ttl", ""),
        old.get("golongan", ""),
        new.get("golongan", ""),
        old.get("jabatan", ""),
        new.get("jabatan", ""),
        old.get("skpd", ""),
        new.get("skpd", ""),
        old.get("pendidikan", ""),
        new.get("pendidikan", ""),
    ]


def compare_data(april_data: list[dict[str, Any]], august_data: list[dict[str, Any]]) -> dict[str, Any]:
    april_by_nip = {only_digits(employee.get("nip")): april_view(employee) for employee in april_data}
    august_by_nip = {only_digits(employee.get("nip")): august_view(employee) for employee in august_data}

    if "" in april_by_nip:
        raise ValueError("Ada NIP kosong pada data April")
    if len(april_by_nip) != len(april_data):
        raise ValueError("Ada NIP duplikat pada data April")

    april_nips = set(april_by_nip)
    august_nips = set(august_by_nip)
    new_nips = sorted(august_nips - april_nips, key=lambda nip: august_by_nip[nip]["no"])
    missing_nips = sorted(april_nips - august_nips, key=lambda nip: april_by_nip[nip]["nama"])
    common_nips = sorted(april_nips & august_nips, key=lambda nip: august_by_nip[nip]["no"])

    common_records: list[dict[str, Any]] = []
    field_counts = Counter()
    for nip in common_nips:
        old = april_by_nip[nip]
        new = august_by_nip[nip]
        changes = changed_fields(old, new)
        field_counts.update(changes)
        common_records.append({"nip": nip, "old": old, "new": new, "changes": changes})

    return {
        "april_by_nip": april_by_nip,
        "august_by_nip": august_by_nip,
        "new_nips": new_nips,
        "missing_nips": missing_nips,
        "common_records": common_records,
        "field_counts": field_counts,
    }


def column_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def safe_xml_text(value: Any) -> str:
    text = str(value if value is not None else "")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
    return escape(text)


def cell_xml(reference: str, value: Any, style: int = 4) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{reference}" s="{style}"><v>{value}</v></c>'
    text = safe_xml_text(value)
    return (
        f'<c r="{reference}" t="inlineStr" s="{style}">'
        f'<is><t xml:space="preserve">{text}</t></is></c>'
    )


def calculate_widths(headers: list[str], rows: list[list[Any]]) -> list[float]:
    widths: list[float] = []
    for column_index, header in enumerate(headers):
        lengths = [len(str(header))]
        for row in rows[:1000]:
            if column_index < len(row):
                lengths.append(max((len(part) for part in str(row[column_index]).split("\n")), default=0))
        maximum = max(lengths, default=10)
        if any(word in header for word in ("SKPD", "Jabatan", "Pendidikan", "Nama/Gelar", "Bidang")):
            widths.append(min(max(maximum + 2, 18), 42))
        elif "NIP" in header:
            widths.append(22)
        else:
            widths.append(min(max(maximum + 2, 11), 28))
    return widths


def worksheet_xml(
    title: str,
    note: str,
    headers: list[str],
    rows: list[list[Any]],
    empty_message: str = "Tidak ada data pada kategori ini.",
) -> str:
    last_column = column_name(len(headers))
    widths = calculate_widths(headers, rows)
    column_xml = "".join(
        f'<col min="{index}" max="{index}" width="{width:.1f}" customWidth="1"/>'
        for index, width in enumerate(widths, start=1)
    )

    xml_rows: list[str] = []
    xml_rows.append(
        f'<row r="1" ht="28" customHeight="1">{cell_xml("A1", title, 1)}</row>'
    )
    xml_rows.append(
        f'<row r="2" ht="32" customHeight="1">{cell_xml("A2", note, 3)}</row>'
    )
    header_cells = "".join(
        cell_xml(f"{column_name(index)}4", header, 2) for index, header in enumerate(headers, start=1)
    )
    xml_rows.append(f'<row r="4" ht="34" customHeight="1">{header_cells}</row>')

    if rows:
        for excel_row, values in enumerate(rows, start=5):
            cells: list[str] = []
            for column_index, value in enumerate(values, start=1):
                style = 5 if column_index in {1, 2, 3, 5, 12, 13} else 4
                cells.append(cell_xml(f"{column_name(column_index)}{excel_row}", value, style))
            xml_rows.append(f'<row r="{excel_row}">{"".join(cells)}</row>')
        last_row = len(rows) + 4
        filter_xml = f'<autoFilter ref="A4:{last_column}{last_row}"/>'
    else:
        xml_rows.append(
            f'<row r="5" ht="24" customHeight="1">{cell_xml("A5", empty_message, 3)}</row>'
        )
        last_row = 5
        filter_xml = ""

    merges = [f'<mergeCell ref="A1:{last_column}1"/>', f'<mergeCell ref="A2:{last_column}2"/>']
    if not rows:
        merges.append(f'<mergeCell ref="A5:{last_column}5"/>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{last_column}{last_row}"/>'
        '<sheetViews><sheetView workbookViewId="0" showGridLines="0">'
        '<pane ySplit="4" topLeftCell="A5" activePane="bottomLeft" state="frozen"/>'
        '</sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="18"/>'
        f'<cols>{column_xml}</cols>'
        f'<sheetData>{"".join(xml_rows)}</sheetData>'
        f'<mergeCells count="{len(merges)}">{"".join(merges)}</mergeCells>'
        f'{filter_xml}'
        '<pageMargins left="0.25" right="0.25" top="0.5" bottom="0.5" header="0.2" footer="0.2"/>'
        '<pageSetup orientation="landscape" fitToWidth="1" fitToHeight="0"/>'
        '</worksheet>'
    )


def styles_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="4">
    <font><sz val="10"/><name val="Calibri"/><family val="2"/></font>
    <font><b/><color rgb="FFFFFFFF"/><sz val="16"/><name val="Calibri"/><family val="2"/></font>
    <font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Calibri"/><family val="2"/></font>
    <font><i/><color rgb="FF44546A"/><sz val="10"/><name val="Calibri"/><family val="2"/></font>
  </fonts>
  <fills count="5">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF17365D"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF4472C4"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFD9EAF7"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border><left style="thin"><color rgb="FFD9E2F3"/></left><right style="thin"><color rgb="FFD9E2F3"/></right><top style="thin"><color rgb="FFD9E2F3"/></top><bottom style="thin"><color rgb="FFD9E2F3"/></bottom><diagonal/></border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="8">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"><alignment horizontal="left" vertical="center"/></xf>
    <xf numFmtId="0" fontId="2" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="3" fillId="4" borderId="0" xfId="0" applyFont="1" applyFill="1"><alignment vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"><alignment vertical="top" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"><alignment horizontal="center" vertical="top" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="2" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"><alignment vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1"><alignment horizontal="center" vertical="center"/></xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''


def write_xlsx(path: Path, sheets: list[tuple[str, str]]) -> None:
    sheet_count = len(sheets)
    content_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        f'{content_overrides}</Types>'
    )
    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''
    workbook_sheets = "".join(
        f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (name, _) in enumerate(sheets, start=1)
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<workbookPr date1904="0"/><bookViews><workbookView activeTab="0"/></bookViews>'
        f'<sheets>{workbook_sheets}</sheets><calcPr calcId="191029"/></workbook>'
    )
    workbook_relationships = "".join(
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, sheet_count + 1)
    )
    workbook_relationships += (
        f'<Relationship Id="rId{sheet_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{workbook_relationships}</Relationships>'
    )

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/styles.xml", styles_xml())
        for index, (_, worksheet) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", worksheet)


def build_report_sheets(
    comparison: dict[str, Any],
    april_count: int,
    august_data: list[dict[str, Any]],
) -> list[tuple[str, str]]:
    april_by_nip = comparison["april_by_nip"]
    august_by_nip = comparison["august_by_nip"]
    new_nips = comparison["new_nips"]
    missing_nips = comparison["missing_nips"]
    common_records = comparison["common_records"]
    field_counts: Counter[str] = comparison["field_counts"]

    changed_common = [record for record in common_records if record["changes"]]
    unchanged_common = [record for record in common_records if not record["changes"]]

    new_rows = [
        report_row(index, "BERTAMBAH DI AGUSTUS", [], None, august_by_nip[nip])
        for index, nip in enumerate(new_nips, start=1)
    ]
    missing_rows = [
        report_row(index, "TIDAK ADA DI AGUSTUS", [], april_by_nip[nip], None)
        for index, nip in enumerate(missing_nips, start=1)
    ]
    common_change_rows = [
        report_row(index, "BERUBAH", record["changes"], record["old"], record["new"])
        for index, record in enumerate(changed_common, start=1)
    ]
    all_change_rows = new_rows + missing_rows + [
        report_row(index, "BERUBAH", record["changes"], record["old"], record["new"])
        for index, record in enumerate(changed_common, start=len(new_rows) + len(missing_rows) + 1)
    ]

    all_common_rows = [
        report_row(
            index,
            "BERUBAH" if record["changes"] else "TETAP",
            record["changes"],
            record["old"],
            record["new"],
        )
        for index, record in enumerate(common_records, start=1)
    ]

    generated_at = datetime.now().astimezone().strftime("%d-%m-%Y %H:%M %Z")
    summary_rows = [
        ["Total data April", april_count, "Jumlah objek pada DUKPNSFULLapril.json"],
        ["Total data Agustus", len(august_data), "Nomor urut 1–845 lengkap"],
        ["NIP cocok di kedua periode", len(common_records), "Pegawai yang dapat dibandingkan langsung"],
        ["Bertambah di Agustus", len(new_nips), "Ada di Agustus, tidak ada di April"],
        ["Tidak ada di Agustus", len(missing_nips), "Ada di April, tidak ditemukan di Agustus"],
        ["Selisih bersih jumlah data", len(august_data) - april_count, "Total Agustus dikurangi total April"],
        ["Data cocok yang berubah", len(changed_common), "Minimal satu bidang pembanding berubah"],
        ["Data cocok tanpa perubahan", len(unchanged_common), "Semua bidang pembanding sama"],
        ["Nama/gelar berubah", field_counts["nama"], "Termasuk penambahan atau perubahan gelar"],
        ["Status/kedudukan berubah", field_counts["status"], "Status PNS/PPPK/CPNS atau aktif/nonaktif"],
        ["Tempat/tanggal lahir berubah", field_counts["ttl"], "Dibandingkan setelah normalisasi format"],
        ["Pangkat/golongan berubah", field_counts["golongan"], "Perubahan golongan ruang"],
        ["Jabatan berubah", field_counts["jabatan"], "Perubahan teks jabatan"],
        ["SKPD berubah", field_counts["skpd"], "Perubahan unit kerja/SKPD"],
        ["Pendidikan terakhir berubah", field_counts["pendidikan"], "Perubahan detail pendidikan yang ditampilkan"],
    ]
    summary_note = (
        f"Dibuat {generated_at}. Pencocokan memakai NIP (hanya digit); perbandingan mengabaikan kapital, "
        "spasi, aksen, dan tanda baca. 'Tidak ada di Agustus' berarti tidak ditemukan pada snapshot, "
        "bukan otomatis berhenti bekerja."
    )

    sheets: list[tuple[str, str]] = [
        (
            "Ringkasan",
            worksheet_xml(
                "Ringkasan Perbandingan PNS — April vs Agustus",
                summary_note,
                ["Metrik", "Jumlah", "Keterangan"],
                summary_rows,
            ),
        ),
        (
            "Semua Perubahan",
            worksheet_xml(
                "Semua Perubahan",
                "Gabungan pegawai bertambah, tidak ada di Agustus, dan pegawai cocok yang memiliki perubahan.",
                REPORT_HEADERS,
                all_change_rows,
            ),
        ),
        (
            "Bertambah",
            worksheet_xml(
                "Pegawai Bertambah di Agustus",
                "NIP ada pada data Agustus tetapi tidak ditemukan pada data April.",
                REPORT_HEADERS,
                new_rows,
            ),
        ),
        (
            "Tidak Ada Agustus",
            worksheet_xml(
                "Pegawai Tidak Ada di Agustus",
                "NIP ada pada data April tetapi tidak ditemukan pada data Agustus; perlu verifikasi status mutasi/pensiun/dll.",
                REPORT_HEADERS,
                missing_rows,
            ),
        ),
    ]

    category_sheets = [
        ("Jabatan Berubah", "jabatan"),
        ("Pangkat Gol Berubah", "golongan"),
        ("SKPD Berubah", "skpd"),
        ("Status Berubah", "status"),
        ("Nama Gelar Berubah", "nama"),
        ("TTL Berubah", "ttl"),
        ("Pendidikan Berubah", "pendidikan"),
    ]
    for sheet_name, field_code in category_sheets:
        records = [record for record in common_records if field_code in record["changes"]]
        rows = [
            report_row(index, "BERUBAH", record["changes"], record["old"], record["new"])
            for index, record in enumerate(records, start=1)
        ]
        sheets.append(
            (
                sheet_name,
                worksheet_xml(
                    sheet_name,
                    f"Pegawai dengan perubahan {FIELD_LABELS[field_code].lower()} pada NIP yang cocok di kedua periode.",
                    REPORT_HEADERS,
                    rows,
                    empty_message=f"Tidak ditemukan perubahan {FIELD_LABELS[field_code].lower()} pada pegawai dengan NIP yang cocok.",
                ),
            )
        )

    sheets.append(
        (
            "Semua NIP Cocok",
            worksheet_xml(
                "Semua Pegawai dengan NIP Cocok",
                "Audit lengkap 838 pegawai yang ada di April dan Agustus, termasuk data berubah maupun tetap.",
                REPORT_HEADERS,
                all_common_rows,
            ),
        )
    )

    august_headers = [
        "No.",
        "ID Pegawai",
        "NIP",
        "Nama/Gelar",
        "Status Kepegawaian",
        "Kedudukan",
        "Tempat Lahir",
        "Tanggal Lahir",
        "Golongan",
        "Jabatan",
        "SKPD",
        "Pendidikan Terakhir",
    ]
    august_rows = [
        [
            employee["no"],
            employee["idPegawai"],
            employee["nip"],
            employee["namaWithGelar"],
            employee["statusKepegawaian"],
            employee["kedudukanKepegawaian"],
            employee["tempatLahir"],
            employee["tanggalLahir"],
            employee["golonganTerakhir"],
            employee["jabatanTerakhir"],
            employee["skpd"],
            employee["pendidikanTerakhir"],
        ]
        for employee in august_data
    ]
    sheets.append(
        (
            "Data Agustus",
            worksheet_xml(
                "Data PNS Agustus yang Sudah Dirapikan",
                "Salinan data terstruktur dari datamentah.txt; versi JSON tersedia pada datapnsagustus.json.",
                august_headers,
                august_rows,
            ),
        )
    )
    return sheets


def main() -> None:
    august_data = parse_august_data(RAW_AUGUST_PATH)
    with APRIL_JSON_PATH.open("r", encoding="utf-8") as file:
        april_data = json.load(file)
    if not isinstance(april_data, list):
        raise ValueError("DUKPNSFULLapril.json harus berupa array JSON")

    with AUGUST_JSON_PATH.open("w", encoding="utf-8") as file:
        json.dump(august_data, file, ensure_ascii=False, indent=2)
        file.write("\n")

    comparison = compare_data(april_data, august_data)
    sheets = build_report_sheets(comparison, len(april_data), august_data)
    write_xlsx(REPORT_PATH, sheets)

    changed_common = sum(bool(record["changes"]) for record in comparison["common_records"])
    print(f"JSON Agustus       : {AUGUST_JSON_PATH.name} ({len(august_data)} pegawai)")
    print(f"Laporan Excel      : {REPORT_PATH.name}")
    print(f"Data April         : {len(april_data)}")
    print(f"NIP cocok          : {len(comparison['common_records'])}")
    print(f"Bertambah          : {len(comparison['new_nips'])}")
    print(f"Tidak ada Agustus  : {len(comparison['missing_nips'])}")
    print(f"Cocok dan berubah  : {changed_common}")
    for field, label in FIELD_LABELS.items():
        print(f"{label:<22}: {comparison['field_counts'][field]}")


if __name__ == "__main__":
    main()
