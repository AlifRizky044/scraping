#!/usr/bin/env python3
"""Insert seven August PNS records into the June DUK workbook.

The workbook is edited at the OOXML level so unsupported Excel parts are kept
byte-for-byte (drawings, relationships, persons, and other metadata).
"""

from __future__ import annotations

import copy
import json
import re
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


BASE_DIR = Path(__file__).resolve().parent
SOURCE_WORKBOOK = Path("/Users/alif/Downloads/DUK BAPENDA KOTA MEDAN 2026 1 Juni 2026 (1).xlsx")
JSON_PATH = BASE_DIR / "DUKPNSFULLagustus.json"
OUTPUT_WORKBOOK = BASE_DIR / "DUK BAPENDA KOTA MEDAN 2026 AGUSTUS UPDATED.xlsx"

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"m": MAIN_NS, "r": REL_NS}
ET.register_namespace("", MAIN_NS)
ET.register_namespace("r", REL_NS)

SHEET_MAIN = "xl/worksheets/sheet1.xml"
SHEET_PNS = "xl/worksheets/sheet2.xml"
SHEET_PPPK_FULL = "xl/worksheets/sheet3.xml"
SHEET_PPPK_PART = "xl/worksheets/sheet4.xml"
SHEET_RECAP = "xl/worksheets/sheet6.xml"
SHARED_STRINGS = "xl/sharedStrings.xml"

UNIT_LABELS = {
    "SEKRETARIAT",
    "BIDANG 1",
    "BIDANG 2",
    "BIDANG 3",
    "BIDANG 4",
    "UPT 1",
    "UPT 2",
    "UPT 3",
    "UPT 4",
    "UPT 5",
    "UPT 6",
    "UPT 7",
}

ACHMAD_NIP = "199107072015071002"

BIDANG_4_NIPS = [
    "198009292000122001",  # AISYAH RAMBE
    "198609112010012040",  # HARISMAH
    "198101212011011007",  # JULHERMAN LUBIS
    "198203102010012029",  # MARTINI AKBAR
    "198703042015031002",  # RIO FERNANDO MANIK
]
IRMA_NIP = "198204202010012027"
ANNA_NIP = "196904161988102001"
ASWAN_NIP = "197606042025211047"

DECEASED_NIPS = {
    ANNA_NIP,
    ASWAN_NIP,
}

PPPK_FULL_BIDANG_4_NIPS = {
    "198002162025212002",  # MELISSA FEBIOLA
    "199903042025211001",  # GIHON KUSY MARPAUNG
    "199002172025211006",  # TODO MUARA MARINUS SIHOTANG
}

BIDANG_4_UNIT = (
    "BIDANG PENGEMBANGAN DAN PENGENDALIAN PAJAK DAN RETRIBUSI DAERAH "
    "BADAN PENDAPATAN DAERAH KOTA MEDAN"
)

NIP_CORRECTIONS = {
    "MIFTACHULLOH": ("198105232025211084", "197905232025211061"),
    "NURHAWANI": ("197212242025212011", "197112242025212010"),
}

REMOVE_FROM_MAIN = {
    "196807161991031003",  # RUSHENDRI
    "196805021990071001",  # ILHAM NUR
    "196802011993122005",  # NURJANI HARAHAP
    "196802212009021001",  # MUHAMMAD MUNIR
    "197110161997031005",  # HERIDJON TUMPAL MARGANDA SIHOMBING
}

REMOVE_FROM_PNS = REMOVE_FROM_MAIN | {
    "196802261997031004",  # SETTA VERO TS
}

REMOVE_FROM_PPPK_PART = {
    "198502242025211056",  # ANANDA ABDINESIA SITEPU
    "198906252025212071",  # SYARAH DHIBA LUBIS
}

AUGUST_RANK_UPDATES = {
    "198107252010011008": "IV/A",    # ALVHANT SYAFRI
    "197703061998031002": "IV/A",    # DARMAWI POHAN
    "198305202010011029": "III/D",   # KOKO MAGRISA FAISAL SIREGAR
    "198605162010012031": "IV/A",    # LAILATUL HUSNA
    "198006112008012019": "III/A",   # MIRANDA
    "198410112010011014": "IV/A",    # MUHAMMAD RIZKY AKBAR HARAHAP
    "197909232010012016": "IV/A",    # SURIYATI
    "198601052005022001": "IV/A",    # YUNITA HANIF
}

RANK_DETAIL_NOT_AVAILABLE = {
    "198107252010011008",  # ALVHANT SYAFRI
    "198305202010011029",  # KOKO MAGRISA FAISAL SIREGAR
    "198006112008012019",  # MIRANDA
}

EXPECTED_NAMES = {
    "199107072015071002": "ACHMAD HUSEIN HARAHAP, S.STP",
    "198009292000122001": "AISYAH RAMBE, S.STP, M.A.P",
    "198609112010012040": "HARISMAH, SEI",
    "198101212011011007": "JULHERMAN LUBIS, S.H.",
    "198203102010012029": "MARTINI AKBAR, S.T.",
    "198703042015031002": "RIO FERNANDO MANIK, S.H.",
    "198204202010012027": "IRMA SARAH MANURUNG, S.E.",
}

RANK_TITLES = {
    "I/A": "Juru Muda (I/a)",
    "I/B": "Juru Muda Tk. I (I/b)",
    "I/C": "Juru (I/c)",
    "I/D": "Juru Tk. I (I/d)",
    "II/A": "Pengatur Muda (II/a)",
    "II/B": "Pengatur Muda Tk. I (II/b)",
    "II/C": "Pengatur (II/c)",
    "II/D": "Pengatur Tk. I (II/d)",
    "III/A": "Penata Muda (III/a)",
    "III/B": "Penata Muda Tk. I (III/b)",
    "III/C": "Penata (III/c)",
    "III/D": "Penata Tk. I (III/d)",
    "IV/A": "Pembina (IV/a)",
    "IV/B": "Pembina Tk. I (IV/b)",
    "IV/C": "Pembina Utama Muda (IV/c)",
    "IV/D": "Pembina Utama Madya (IV/d)",
    "IV/E": "Pembina Utama (IV/e)",
}

UNIT_RECAP_ROWS = {
    "SEKRETARIAT": 4,
    "BIDANG 1": 5,
    "BIDANG 2": 6,
    "BIDANG 3": 7,
    "BIDANG 4": 8,
    "UPT 1": 9,
    "UPT 2": 10,
    "UPT 3": 11,
    "UPT 4": 12,
    "UPT 5": 13,
    "UPT 6": 14,
    "UPT 7": 15,
}

JOB_RECAP_ROWS = {
    "ESELON II": 21,
    "ESELON III": 22,
    "ESELON IV": 23,
    "FUNGSIONAL": 24,
    "STAF": 25,
}

RANK_RECAP_ROWS = {
    "IV/C": 31,
    "IV/B": 32,
    "IV/A": 33,
    "III/D": 34,
    "III/C": 35,
    "III/B": 36,
    "III/A": 37,
    "II/D": 38,
    "II/C": 39,
    "II/B": 40,
    "II/A": 41,
    "I/D": 42,
    "I/C": 43,
    "I/B": 44,
    "I/A": 45,
}

EDUCATION_RECAP_ROWS = {
    "S3": 51,
    "S2": 52,
    "S1": 53,
    "DIPLOMA": 54,
    "SLTA": 55,
    "SLTP": 56,
    "SD": 57,
}


def tag(name: str) -> str:
    return f"{{{MAIN_NS}}}{name}"


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def col_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def cell_col(reference: str) -> str:
    match = re.match(r"([A-Z]+)", reference)
    return match.group(1) if match else ""


def parse_date(value: Any) -> date | None:
    text = clean(value)
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def excel_serial(value: date | None) -> float | None:
    if value is None:
        return None
    return float((value - date(1899, 12, 30)).days)


def calculate_bup(employee: dict[str, Any], eselon: str) -> float | None:
    birth = parse_date(employee.get("tanggalLahir"))
    if birth is None:
        return None
    retirement_age = 60 if clean(eselon).upper().startswith("II.") else 58
    year = birth.year + retirement_age
    month = birth.month + 1
    if month == 13:
        month = 1
        year += 1
    return excel_serial(date(year, month, 1))


def latest_list_item(value: Any) -> dict[str, Any]:
    if isinstance(value, list) and value and isinstance(value[-1], dict):
        return value[-1]
    return {}


def rank_group(rank_text: str) -> str:
    match = re.search(r"\(([IVX]+/[A-E])\)", clean(rank_text).upper())
    return match.group(1) if match else ""


def integer_or_blank(value: Any) -> int | None:
    text = clean(value)
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def build_excel_row(employee: dict[str, Any]) -> list[Any]:
    """Map a DUKPNSFULL object into the workbook's 44 columns (A:AR)."""
    rank_history = employee.get("riwayatPangkat")
    job_history = employee.get("riwayatJabatan")
    education_history = employee.get("riwayatPendidikan")
    structural_training = employee.get("riwayatDiklatStruktural")

    first_rank = rank_history[0] if isinstance(rank_history, list) and rank_history else {}
    latest_rank = latest_list_item(rank_history)
    latest_job = latest_list_item(job_history)
    latest_education = latest_list_item(education_history)
    latest_training = latest_list_item(structural_training)

    row: list[Any] = [None] * 44
    row[1] = clean(employee.get("namaWithGelar")).upper()
    row[2] = "'" + digits(employee.get("nip"))
    row[3] = integer_or_blank(latest_rank.get("mkgTahun"))
    row[4] = integer_or_blank(latest_rank.get("mkgBulan"))
    row[5] = clean(first_rank.get("pangkat"))
    row[6] = rank_group(clean(first_rank.get("pangkat")))
    row[7] = excel_serial(parse_date(first_rank.get("tmt")))
    history_group = rank_group(clean(latest_rank.get("pangkat")))
    current_group = clean(employee.get("golonganTerakhir")).upper() or history_group
    row[8] = clean(latest_rank.get("pangkat"))
    row[9] = current_group
    row[10] = clean(latest_rank.get("noSk"))
    row[11] = clean(latest_rank.get("pejabatPenandatangan"))
    row[12] = excel_serial(parse_date(latest_rank.get("tmt")))
    # The August summary can contain a newly effective rank before its detailed
    # SK history is available.  Use the authoritative rank/golongan, but never
    # carry the older SK/TMT forward as if it belonged to the promotion.
    if current_group and current_group != history_group:
        row[8] = RANK_TITLES.get(current_group, current_group)
        row[10] = None
        row[11] = None
        row[12] = None
    current_job = clean(employee.get("jabatanTerakhir") or latest_job.get("jabatan")).upper()
    history_job = clean(latest_job.get("jabatan")).upper()
    current_unit = clean(employee.get("skpd") or latest_job.get("skpd")).upper()
    history_unit = clean(latest_job.get("skpd")).upper()
    current_job_key = canonical_job(current_job)
    history_job_key = canonical_job(history_job)
    current_unit_key = canonical_job(current_unit)
    history_unit_key = canonical_job(history_unit)
    job_title_is_current = bool(
        current_job_key
        and history_job_key
        and (current_job_key in history_job_key or history_job_key in current_job_key)
    )
    job_unit_is_current = bool(
        current_unit_key
        and history_unit_key
        and (current_unit_key in history_unit_key or history_unit_key in current_unit_key)
    )
    job_history_is_current = job_title_is_current and job_unit_is_current
    job_type = clean(latest_job.get("tipeJabatan"))
    eselon = clean(latest_job.get("eselon"))
    functional_titles = (
        "ANALIS SUMBER DAYA MANUSIA APARATUR MUDA",
        "ANALIS KEUANGAN PUSAT DAN DAERAH MUDA",
        "ARSIPARIS PERTAMA",
        "PERENCANA MUDA",
    )
    if any(title in current_job for title in functional_titles):
        job_type = "Fungsional Tertentu"
        eselon = ""
    elif current_job.startswith("KEPALA BADAN "):
        job_type, eselon = "Struktural", "II.b"
    elif current_job.startswith("SEKRETARIS BADAN"):
        job_type, eselon = "Struktural", "III.a"
    elif current_job.startswith("KEPALA BIDANG"):
        job_type, eselon = "Struktural", "III.b"
    elif current_job.startswith(("KEPALA UPT", "KEPALA SUB ")):
        job_type, eselon = "Struktural", "IV.a"
    elif not job_history_is_current:
        job_type, eselon = "Fungsional Umum / Pelaksana", ""

    row[13] = job_type
    row[14] = current_job
    row[15] = eselon
    # The August list is authoritative for the current unit; history can be older.
    row[16] = current_unit
    row[17] = excel_serial(parse_date(latest_job.get("tmt")))
    row[18] = clean(latest_job.get("tmtSk"))
    row[19] = None
    row[20] = clean(latest_job.get("pejabatPenetapan"))
    if not job_history_is_current:
        row[17] = None
        row[18] = None
        row[20] = None
    row[21] = clean(latest_education.get("tingkatPendidikan"))
    row[22] = clean(latest_education.get("jurusan"))
    row[23] = clean(latest_education.get("namaSekolah"))
    row[24] = clean(latest_education.get("tanggalIjazah"))
    row[25] = clean(latest_training.get("namaDiklat"))
    row[26] = calculate_bup(employee, row[15] or "")
    row[27] = None
    row[28] = None  # Helper is recomputed for the whole sheet after insertion.
    row[29] = clean(employee.get("statusKepegawaian"))
    row[30] = clean(employee.get("agama"))
    row[31] = clean(employee.get("statusPernikahan"))
    row[32] = clean(employee.get("jenisKelamin"))
    row[33] = clean(employee.get("golDarah"))
    row[34] = clean(employee.get("noHp"))
    row[35] = clean(employee.get("email"))
    row[36] = clean(employee.get("tempatTglLahir")).replace("\n", ", ").upper()
    row[37] = clean(employee.get("alamat"))
    row[38] = clean(employee.get("provinsi"))
    row[39] = clean(employee.get("kota"))
    row[40] = clean(employee.get("kecamatan"))
    row[41] = clean(employee.get("kelurahan"))
    row[42] = clean(employee.get("rt"))
    row[43] = clean(employee.get("rw"))
    return row


class SharedStringStore:
    def __init__(self, xml_bytes: bytes) -> None:
        self.root = ET.fromstring(xml_bytes)
        self.items = self.root.findall(tag("si"))
        self.lookup: dict[str, int] = {}
        for index, item in enumerate(self.items):
            text_value = "".join(node.text or "" for node in item.iter(tag("t")))
            self.lookup.setdefault(text_value, index)
        self.total_occurrences = int(self.root.get("count", "0"))

    def index(self, value: str) -> int:
        if value in self.lookup:
            return self.lookup[value]
        item = ET.SubElement(self.root, tag("si"))
        text_node = ET.SubElement(item, tag("t"))
        if value[:1].isspace() or value[-1:].isspace() or "\n" in value:
            text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        text_node.text = value
        index = len(self.items)
        self.items.append(item)
        self.lookup[value] = index
        return index

    def adjust_occurrences(self, amount: int) -> None:
        self.total_occurrences += amount

    def to_bytes(self) -> bytes:
        self.root.set("count", str(self.total_occurrences))
        self.root.set("uniqueCount", str(len(self.items)))
        return ET.tostring(self.root, encoding="utf-8", xml_declaration=True)


def cell_text(cell: ET.Element | None, shared: SharedStringStore) -> str:
    if cell is None:
        return ""
    value_node = cell.find(tag("v"))
    if value_node is None or value_node.text is None:
        inline = cell.find(f"{tag('is')}/{tag('t')}")
        return inline.text if inline is not None and inline.text else ""
    if cell.get("t") == "s":
        try:
            index = int(value_node.text)
            item = shared.items[index]
            return "".join(node.text or "" for node in item.iter(tag("t")))
        except (ValueError, IndexError):
            return ""
    return value_node.text


def get_cell(row: ET.Element, column: str) -> ET.Element | None:
    for cell in row.findall(tag("c")):
        if cell_col(cell.get("r", "")) == column:
            return cell
    return None


def ensure_cell(row: ET.Element, column: str, row_number: int, template: ET.Element | None = None) -> ET.Element:
    existing = get_cell(row, column)
    if existing is not None:
        return existing
    cell = copy.deepcopy(template) if template is not None else ET.Element(tag("c"))
    cell.set("r", f"{column}{row_number}")
    cells = row.findall(tag("c"))
    target_index = 0
    target_col_number = 0
    for char in column:
        target_col_number = target_col_number * 26 + ord(char) - 64
    while target_index < len(cells):
        current = cell_col(cells[target_index].get("r", ""))
        current_number = 0
        for char in current:
            current_number = current_number * 26 + ord(char) - 64
        if current_number > target_col_number:
            break
        target_index += 1
    row.insert(target_index, cell)
    return cell


def clear_cell_content(cell: ET.Element) -> None:
    for child in list(cell):
        cell.remove(child)
    cell.attrib.pop("t", None)


def set_cell_value(
    cell: ET.Element,
    value: Any,
    shared: SharedStringStore,
    *,
    new_occurrence: bool = False,
) -> None:
    had_shared_string = (
        not new_occurrence
        and cell.get("t") == "s"
        and cell.find(tag("v")) is not None
    )
    has_shared_string = value is not None and value != "" and not (
        isinstance(value, (int, float)) and not isinstance(value, bool)
    )
    shared.adjust_occurrences(int(has_shared_string) - int(had_shared_string))
    clear_cell_content(cell)
    if value is None or value == "":
        return
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value_node = ET.SubElement(cell, tag("v"))
        if isinstance(value, float) and value.is_integer():
            value_node.text = str(int(value))
        else:
            value_node.text = str(value)
        return
    cell.set("t", "s")
    value_node = ET.SubElement(cell, tag("v"))
    value_node.text = str(shared.index(str(value)))


def set_formula_cell(cell: ET.Element, formula: str, cached_value: int) -> None:
    clear_cell_content(cell)
    formula_node = ET.SubElement(cell, tag("f"))
    formula_node.text = formula
    value_node = ET.SubElement(cell, tag("v"))
    value_node.text = str(cached_value)


CELL_REF_RE = re.compile(r"(\$?[A-Z]{1,3}\$?)(\d+)")


def shift_reference(reference: str, start_row: int, amount: int) -> str:
    def replace(match: re.Match[str]) -> str:
        row_number = int(match.group(2))
        if row_number >= start_row:
            row_number += amount
        return f"{match.group(1)}{row_number}"

    return CELL_REF_RE.sub(replace, reference)


def shift_sheet_metadata(root: ET.Element, start_row: int, amount: int) -> None:
    for element_name, attribute in (
        ("mergeCell", "ref"),
        ("hyperlink", "ref"),
        ("autoFilter", "ref"),
        ("conditionalFormatting", "sqref"),
        ("dataValidation", "sqref"),
    ):
        for element in root.findall(f".//{tag(element_name)}"):
            value = element.get(attribute)
            if value:
                element.set(attribute, " ".join(shift_reference(part, start_row, amount) for part in value.split()))
    for page_break in root.findall(f".//{tag('brk')}"):
        break_id = page_break.get("id")
        if break_id and break_id.isdigit() and int(break_id) >= start_row:
            page_break.set("id", str(int(break_id) + amount))


def shift_existing_rows(root: ET.Element, start_row: int, amount: int) -> None:
    sheet_data = root.find(tag("sheetData"))
    if sheet_data is None:
        raise ValueError("sheetData tidak ditemukan")
    for row in reversed(sheet_data.findall(tag("row"))):
        row_number = int(row.get("r", "0"))
        if row_number < start_row:
            continue
        new_row_number = row_number + amount
        row.set("r", str(new_row_number))
        for cell in row.findall(tag("c")):
            column = cell_col(cell.get("r", ""))
            cell.set("r", f"{column}{new_row_number}")
    shift_sheet_metadata(root, start_row, amount)


def find_row(root: ET.Element, row_number: int) -> ET.Element:
    sheet_data = root.find(tag("sheetData"))
    if sheet_data is None:
        raise ValueError("sheetData tidak ditemukan")
    for row in sheet_data.findall(tag("row")):
        if int(row.get("r", "0")) == row_number:
            return row
    raise ValueError(f"Baris {row_number} tidak ditemukan")


def insert_employee_rows(
    root: ET.Element,
    shared: SharedStringStore,
    insert_at: int,
    template_row_number: int,
    employee_rows: list[list[Any]],
    column_count: int = 44,
) -> None:
    template_row = copy.deepcopy(find_row(root, template_row_number))
    amount = len(employee_rows)
    shift_existing_rows(root, insert_at, amount)

    sheet_data = root.find(tag("sheetData"))
    assert sheet_data is not None
    all_rows = sheet_data.findall(tag("row"))
    insertion_index = next(
        (index for index, row in enumerate(all_rows) if int(row.get("r", "0")) >= insert_at),
        len(all_rows),
    )

    for offset, values in enumerate(employee_rows):
        row_number = insert_at + offset
        new_row = copy.deepcopy(template_row)
        new_row.set("r", str(row_number))
        template_cells = {cell_col(cell.get("r", "")): cell for cell in new_row.findall(tag("c"))}
        for column_index in range(1, column_count + 1):
            column = col_name(column_index)
            cell = ensure_cell(new_row, column, row_number, template_cells.get(column))
            cell.set("r", f"{column}{row_number}")
            set_cell_value(cell, values[column_index - 1], shared, new_occurrence=True)
        sheet_data.insert(insertion_index + offset, new_row)


def update_row_columns(
    row: ET.Element,
    row_number: int,
    values_by_index: dict[int, Any],
    shared: SharedStringStore,
) -> None:
    """Update selected zero-based columns while keeping each cell's style."""
    for zero_based_index, value in values_by_index.items():
        column = col_name(zero_based_index + 1)
        cell = ensure_cell(row, column, row_number)
        set_cell_value(cell, value, shared)


def employee_values_for_sheet(employee: dict[str, Any], sheet_kind: str) -> dict[int, Any]:
    full = build_excel_row(employee)
    status = clean(employee.get("statusKepegawaian")).upper()

    if sheet_kind in {"main", "pns"} and status in {"PNS", "CPNS"}:
        # A is numbering and AC is a helper sequence; both are recomputed.
        return {index: full[index] for index in range(1, 44) if index != 28}

    if sheet_kind == "main" and status == "PPPK":
        # Preserve PPPK appointment fields which are not present in the August
        # JSON, while refreshing all fields for which August data is available.
        indices = [
            1, 2, 14, 21, 22, 23, 24,
            29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43,
        ]
        return {index: full[index] for index in indices}

    if sheet_kind == "pppk_full" and status == "PPPK":
        result = {
            1: full[1],
            2: full[2],
            9: full[14],
        }
        result.update({15 + offset: full[21 + offset] for offset in range(4)})
        result.update({20 + offset: full[29 + offset] for offset in range(15)})
        return result

    if sheet_kind == "pppk_part" and status == "PPPK":
        result = {
            1: full[1],
            2: full[2],
            7: full[14],
        }
        result.update({9 + offset: full[21 + offset] for offset in range(4)})
        result.update({13 + offset: full[30 + offset] for offset in range(14)})
        return result

    return {}


def update_matching_employee_rows(
    root: ET.Element,
    shared: SharedStringStore,
    employee_by_nip: dict[str, dict[str, Any]],
    sheet_kind: str,
) -> int:
    sheet_data = root.find(tag("sheetData"))
    if sheet_data is None:
        raise ValueError("sheetData tidak ditemukan")
    updated = 0
    for row in sheet_data.findall(tag("row")):
        nip = digits(cell_text(get_cell(row, "C"), shared))
        employee = employee_by_nip.get(nip)
        if employee is None:
            continue
        values = employee_values_for_sheet(employee, sheet_kind)
        if not values:
            continue
        row_number = int(row.get("r", "0"))
        update_row_columns(row, row_number, values, shared)
        updated += 1
    return updated


def repair_employee_nip_by_name(
    root: ET.Element,
    shared: SharedStringStore,
    employee: dict[str, Any],
    expected_old_nip: str,
    sheet_kind: str,
) -> None:
    row_number = find_employee_row_by_name(root, shared, clean(employee.get("namaWithGelar")).upper())
    row = find_row(root, row_number)
    actual_old_nip = digits(cell_text(get_cell(row, "C"), shared))
    if actual_old_nip != expected_old_nip:
        raise ValueError(
            f"NIP lama {employee.get('namaWithGelar')} pada {sheet_kind} adalah "
            f"{actual_old_nip}, seharusnya {expected_old_nip}"
        )
    update_row_columns(
        row,
        row_number,
        employee_values_for_sheet(employee, sheet_kind),
        shared,
    )


def remove_employee_rows_by_nip(
    root: ET.Element,
    shared: SharedStringStore,
    nips: set[str],
) -> list[str]:
    sheet_data = root.find(tag("sheetData"))
    if sheet_data is None:
        raise ValueError("sheetData tidak ditemukan")
    targets: list[tuple[int, ET.Element, str]] = []
    for row in sheet_data.findall(tag("row")):
        nip = digits(cell_text(get_cell(row, "C"), shared))
        if nip in nips:
            targets.append((int(row.get("r", "0")), row, nip))
    found = {nip for _, _, nip in targets}
    if found != nips:
        raise ValueError(f"NIP yang akan dikeluarkan tidak lengkap: ditemukan={sorted(found)}, diminta={sorted(nips)}")

    removed: list[str] = []
    for row_number, row, nip in sorted(targets, reverse=True):
        shared_occurrences = sum(
            1
            for cell in row.findall(tag("c"))
            if cell.get("t") == "s" and cell.find(tag("v")) is not None
        )
        shared.adjust_occurrences(-shared_occurrences)
        sheet_data.remove(row)
        shift_existing_rows(root, row_number + 1, -1)
        removed.append(nip)
    return removed


def find_unit_header_rows(root: ET.Element, shared: SharedStringStore, unit: str) -> list[int]:
    sheet_data = root.find(tag("sheetData"))
    if sheet_data is None:
        raise ValueError("sheetData tidak ditemukan")
    target = clean(unit).upper()
    return [
        int(row.get("r", "0"))
        for row in sheet_data.findall(tag("row"))
        if clean(cell_text(get_cell(row, "B"), shared)).upper() == target
    ]


def previous_employee_row(root: ET.Element, shared: SharedStringStore, before_row: int) -> int:
    sheet_data = root.find(tag("sheetData"))
    if sheet_data is None:
        raise ValueError("sheetData tidak ditemukan")
    candidates = [
        int(row.get("r", "0"))
        for row in sheet_data.findall(tag("row"))
        if int(row.get("r", "0")) < before_row and is_employee_row(row, shared)
    ]
    if not candidates:
        raise ValueError(f"Template pegawai sebelum baris {before_row} tidak ditemukan")
    return max(candidates)


def values_for_new_sheet_row(
    employee: dict[str, Any],
    sheet_kind: str,
    column_count: int,
) -> list[Any]:
    if sheet_kind in {"main", "pns"} and clean(employee.get("statusKepegawaian")).upper() in {"PNS", "CPNS"}:
        return build_excel_row(employee)
    values: list[Any] = [None] * column_count
    for index, value in employee_values_for_sheet(employee, sheet_kind).items():
        values[index] = value
    # Existing PPPK rows retain their more specific workbook unit because the
    # August summary often only says "Badan Pendapatan Daerah".  A genuinely
    # new row still needs the available August unit written explicitly.
    if sheet_kind == "main":
        values[16] = clean(employee.get("skpd")).upper()
    elif sheet_kind == "pppk_full":
        values[10] = clean(employee.get("skpd")).upper()
    elif sheet_kind == "pppk_part":
        values[8] = clean(employee.get("skpd")).upper()
    return values


def insert_employee_before_unit(
    root: ET.Element,
    shared: SharedStringStore,
    employee: dict[str, Any],
    unit_after: str,
    sheet_kind: str,
    column_count: int,
) -> None:
    headers = find_unit_header_rows(root, shared, unit_after)
    if len(headers) != 1:
        raise ValueError(f"Header {unit_after} pada {sheet_kind} berjumlah {len(headers)}, seharusnya 1")
    insert_at = headers[0]
    template_row = previous_employee_row(root, shared, insert_at)
    values = values_for_new_sheet_row(employee, sheet_kind, column_count)
    insert_employee_rows(
        root,
        shared,
        insert_at,
        template_row,
        [values],
        column_count=column_count,
    )


def recompute_simple_numbering(
    root: ET.Element,
    shared: SharedStringStore,
    column_count: int,
) -> int:
    sheet_data = root.find(tag("sheetData"))
    if sheet_data is None:
        raise ValueError("sheetData tidak ditemukan")
    counter = 0
    previous_row: int | None = None
    max_row = 1
    for row in sorted(sheet_data.findall(tag("row")), key=lambda item: int(item.get("r", "0"))):
        row_number = int(row.get("r", "0"))
        max_row = max(max_row, row_number)
        if not is_employee_row(row, shared):
            continue
        counter += 1
        cell_a = ensure_cell(row, "A", row_number)
        if previous_row is None:
            set_cell_value(cell_a, 1, shared)
        else:
            set_formula_cell(cell_a, f"SUM(A{previous_row}+1)", counter)
        previous_row = row_number
    dimension = root.find(tag("dimension"))
    if dimension is not None:
        dimension.set("ref", f"A1:{col_name(column_count)}{max_row}")
    return counter


def employee_nips(root: ET.Element, shared: SharedStringStore) -> list[str]:
    sheet_data = root.find(tag("sheetData"))
    if sheet_data is None:
        raise ValueError("sheetData tidak ditemukan")
    return [
        digits(cell_text(get_cell(row, "C"), shared))
        for row in sheet_data.findall(tag("row"))
        if is_employee_row(row, shared)
    ]


def set_unit_for_nips(
    root: ET.Element,
    shared: SharedStringStore,
    nips: set[str],
    unit_column: str,
    unit_value: str,
) -> None:
    for nip in nips:
        row_number = find_employee_row_by_nip(root, shared, nip)
        row = find_row(root, row_number)
        cell = ensure_cell(row, unit_column, row_number)
        set_cell_value(cell, unit_value, shared)


def validate_exact_rosters(
    main_root: ET.Element,
    pns_root: ET.Element,
    pppk_full_root: ET.Element,
    pppk_part_root: ET.Element,
    shared: SharedStringStore,
    employee_by_nip: dict[str, dict[str, Any]],
) -> None:
    expected_all = set(employee_by_nip) - DECEASED_NIPS
    expected_pns = {
        nip
        for nip, employee in employee_by_nip.items()
        if nip in expected_all
        and clean(employee.get("statusKepegawaian")).upper() in {"PNS", "CPNS"}
    }
    expected_pppk = expected_all - expected_pns
    actual_main = employee_nips(main_root, shared)
    actual_pns = employee_nips(pns_root, shared)
    actual_full = employee_nips(pppk_full_root, shared)
    actual_part = employee_nips(pppk_part_root, shared)

    for label, values in (
        ("sheet utama", actual_main),
        ("sheet PNS", actual_pns),
        ("sheet PPPK penuh", actual_full),
        ("sheet PPPK paruh", actual_part),
    ):
        if len(values) != len(set(values)):
            raise ValueError(f"Ada NIP ganda pada {label}")

    if set(actual_main) != expected_all:
        raise ValueError(
            f"Roster utama belum sama dengan Agustus: kurang={sorted(expected_all - set(actual_main))}, "
            f"lebih={sorted(set(actual_main) - expected_all)}"
        )
    if set(actual_pns) != expected_pns:
        raise ValueError(
            f"Roster PNS belum sama dengan Agustus: kurang={sorted(expected_pns - set(actual_pns))}, "
            f"lebih={sorted(set(actual_pns) - expected_pns)}"
        )
    actual_pppk = set(actual_full) | set(actual_part)
    if set(actual_full) & set(actual_part):
        raise ValueError("Ada NIP PPPK yang muncul pada sheet penuh dan paruh waktu")
    if actual_pppk != expected_pppk:
        raise ValueError(
            f"Roster PPPK belum sama dengan Agustus: kurang={sorted(expected_pppk - actual_pppk)}, "
            f"lebih={sorted(actual_pppk - expected_pppk)}"
        )


def is_employee_row(row: ET.Element, shared: SharedStringStore) -> bool:
    nip = digits(cell_text(get_cell(row, "C"), shared))
    return len(nip) >= 15


def recompute_numbering_and_helper(root: ET.Element, shared: SharedStringStore) -> int:
    sheet_data = root.find(tag("sheetData"))
    if sheet_data is None:
        raise ValueError("sheetData tidak ditemukan")
    counter = 0
    previous_employee_row: int | None = None
    max_row = 1
    for row in sorted(sheet_data.findall(tag("row")), key=lambda item: int(item.get("r", "0"))):
        row_number = int(row.get("r", "0"))
        max_row = max(max_row, row_number)
        if is_employee_row(row, shared):
            counter += 1
            cell_a = ensure_cell(row, "A", row_number)
            if previous_employee_row is None:
                set_cell_value(cell_a, 1, shared)
            else:
                set_formula_cell(cell_a, f"SUM(A{previous_employee_row}+1)", counter)
            cell_ac = ensure_cell(row, "AC", row_number)
            set_cell_value(cell_ac, counter, shared)
            previous_employee_row = row_number
        else:
            unit = clean(cell_text(get_cell(row, "B"), shared)).upper()
            if unit in UNIT_LABELS:
                cell_ac = ensure_cell(row, "AC", row_number)
                set_cell_value(cell_ac, counter, shared)

    dimension = root.find(tag("dimension"))
    if dimension is not None:
        dimension.set("ref", f"A1:AR{max_row}")
    return counter


def parse_sheet(xml_bytes: bytes) -> ET.Element:
    return ET.fromstring(xml_bytes)


def sheet_to_bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def find_employee_row_by_name(root: ET.Element, shared: SharedStringStore, name: str) -> int:
    sheet_data = root.find(tag("sheetData"))
    assert sheet_data is not None
    target = clean(name).upper()
    for row in sheet_data.findall(tag("row")):
        current = clean(cell_text(get_cell(row, "B"), shared)).upper()
        if current == target:
            return int(row.get("r", "0"))
    raise ValueError(f"Nama anchor tidak ditemukan: {name}")


def find_employee_row_by_nip(root: ET.Element, shared: SharedStringStore, nip: str) -> int:
    sheet_data = root.find(tag("sheetData"))
    assert sheet_data is not None
    for row in sheet_data.findall(tag("row")):
        current = digits(cell_text(get_cell(row, "C"), shared))
        if current == nip:
            return int(row.get("r", "0"))
    raise ValueError(f"NIP tidak ditemukan: {nip}")


def set_numeric_cache_or_value(root: ET.Element, reference: str, number: int) -> None:
    match = re.fullmatch(r"([A-Z]+)(\d+)", reference)
    if not match:
        raise ValueError(f"Referensi sel tidak valid: {reference}")
    row = find_row(root, int(match.group(2)))
    cell = get_cell(row, match.group(1))
    if cell is None:
        cell = ensure_cell(row, match.group(1), int(match.group(2)))
    formula = cell.find(tag("f"))
    if formula is None:
        clear_cell_content(cell)
    else:
        for value_node in cell.findall(tag("v")):
            cell.remove(value_node)
        cell.attrib.pop("t", None)
    value_node = ET.SubElement(cell, tag("v"))
    value_node.text = str(number)


def normalize_rank(value: str) -> str:
    normalized = clean(value).upper().replace(".", "/").replace(" ", "")
    match = re.fullmatch(r"(IV|III|II|I)/?([A-E])", normalized)
    return f"{match.group(1)}/{match.group(2)}" if match else ""


def classify_education(*values: str) -> str:
    text = " ".join(clean(value).upper() for value in values)
    if any(key in text for key in ("STRATA - 3", "STRATA 3", "S3", "DOKTOR")):
        return "S3"
    if any(key in text for key in ("STRATA - 2", "STRATA 2", "S2", "MAGISTER")):
        return "S2"
    if (
        any(key in text for key in ("STRATA - 1", "STRATA 1", "S1", "SARJANA"))
        and "SARJANA TERAPAN" not in text
    ):
        return "S1"
    if any(
        key in text
        for key in (
            "DIPLOMA", "D-I", "D-II", "D-III", "D-IV", "D1", "D2", "D3", "D4",
            "SARJANA TERAPAN", "AHLI MADYA",
        )
    ):
        return "DIPLOMA"
    if any(key in text for key in ("SLTA", "SMA", "SMK", "STM", "AMK", "ALIYAH", "MA ")):
        return "SLTA"
    if any(key in text for key in ("SLTP", "SMP", "MTS")):
        return "SLTP"
    if " SD" in f" {text}" or text.startswith("SD "):
        return "SD"
    return ""


def classify_unit_text(value: str) -> str:
    unit = clean(value).upper()
    match = re.search(r"WILAYAH\s+(I|II|III|IV|V|VI|VII)\b", unit)
    if match:
        roman_to_number = {
            "I": "1", "II": "2", "III": "3", "IV": "4",
            "V": "5", "VI": "6", "VII": "7",
        }
        return f"UPT {roman_to_number[match.group(1)]}"
    if "PENGEMBANGAN DAN PENGENDALIAN" in unit:
        return "BIDANG 4"
    if any(key in unit for key in ("PARKIR", "REKLAME", "PENERANGAN JALAN", "AIR TANAH", "WALET", "RETRIBUSI")):
        return "BIDANG 2"
    if any(key in unit for key in ("HOTEL", "RESTORAN", "HIBURAN")):
        return "BIDANG 1"
    if any(key in unit for key in ("BEA PEROLEHAN HAK ATAS TANAH", "PAJAK BUMI DAN BANGUNAN")):
        return "BIDANG 3"
    return "SEKRETARIAT"


def collect_unit_counts_from_sheet(
    root: ET.Element,
    shared: SharedStringStore,
    unit_column: str,
) -> dict[str, int]:
    counts = {unit: 0 for unit in UNIT_RECAP_ROWS}
    sheet_data = root.find(tag("sheetData"))
    if sheet_data is None:
        raise ValueError("sheetData tidak ditemukan")
    for row in sheet_data.findall(tag("row")):
        if not is_employee_row(row, shared):
            continue
        unit = classify_unit_text(cell_text(get_cell(row, unit_column), shared))
        counts[unit] += 1
    return counts


def collect_physical_unit_counts(
    root: ET.Element,
    shared: SharedStringStore,
) -> dict[str, int]:
    counts = {unit: 0 for unit in UNIT_RECAP_ROWS}
    sheet_data = root.find(tag("sheetData"))
    if sheet_data is None:
        raise ValueError("sheetData tidak ditemukan")
    current_unit = "SEKRETARIAT"
    for row in sorted(sheet_data.findall(tag("row")), key=lambda item: int(item.get("r", "0"))):
        label = clean(cell_text(get_cell(row, "B"), shared)).upper()
        if label in UNIT_RECAP_ROWS:
            current_unit = label
            continue
        if is_employee_row(row, shared):
            counts[current_unit] += 1
    return counts


def gender_key(value: str) -> str:
    normalized = clean(value).upper()
    if normalized.startswith("LAKI"):
        return "male"
    if normalized.startswith("PEREMPUAN"):
        return "female"
    return ""


def classify_job(current_job_value: str, eselon_value: str, type_value: str) -> str:
    current_job = canonical_job(current_job_value)
    if current_job.startswith("KEPALA BADAN "):
        return "ESELON II"
    if current_job.startswith(("SEKRETARIS BADAN", "KEPALA BIDANG")):
        return "ESELON III"
    if current_job.startswith(("KEPALA UPT", "KEPALA SUB ")):
        return "ESELON IV"
    eselon = clean(eselon_value).upper().replace(".", " ")
    match = re.match(r"^(II|III|IV)\b", eselon)
    if match:
        return f"ESELON {match.group(1)}"
    job_type = clean(type_value).upper()
    if "FUNGSIONAL" in job_type and "UMUM" not in job_type and "PELAKSANA" not in job_type:
        return "FUNGSIONAL"
    return "STAF"


def canonical_job(value: str) -> str:
    normalized = clean(value).upper()
    normalized = normalized.replace("SUBBAGIAN", "SUB BAGIAN").replace("SUBBIDANG", "SUB BIDANG")
    normalized = re.sub(r"\bAHLI\b", " ", normalized)
    return re.sub(r"[^A-Z0-9]+", " ", normalized).strip()


def numeric_cell(root: ET.Element, reference: str) -> int:
    match = re.fullmatch(r"([A-Z]+)(\d+)", reference)
    if not match:
        raise ValueError(f"Referensi sel tidak valid: {reference}")
    cell = get_cell(find_row(root, int(match.group(2))), match.group(1))
    value = cell.find(tag("v")) if cell is not None else None
    try:
        return int(float(value.text or "0")) if value is not None else 0
    except ValueError:
        return 0


def collect_pns_recap(
    pns_root: ET.Element,
    recap_root: ET.Element,
    shared: SharedStringStore,
) -> dict[str, Any]:
    unit_counts = {key: 0 for key in UNIT_RECAP_ROWS}
    job_counts = {key: {"male": 0, "female": 0} for key in JOB_RECAP_ROWS}
    rank_counts = {key: {"male": 0, "female": 0} for key in RANK_RECAP_ROWS}
    education_counts = {key: {"male": 0, "female": 0} for key in EDUCATION_RECAP_ROWS}
    formation_counts = {row: 0 for row in range(63, 102)}
    formation_labels = {
        row_number: canonical_job(cell_text(get_cell(find_row(recap_root, row_number), "B"), shared))
        for row_number in range(63, 101)
    }

    sheet_data = pns_root.find(tag("sheetData"))
    if sheet_data is None:
        raise ValueError("sheetData PNS tidak ditemukan")
    # The first physical block is Sekretariat and has no separate section row.
    current_unit = "SEKRETARIAT"
    employee_total = 0
    problems: list[str] = []

    for row in sorted(sheet_data.findall(tag("row")), key=lambda item: int(item.get("r", "0"))):
        label = clean(cell_text(get_cell(row, "B"), shared)).upper()
        if label in UNIT_RECAP_ROWS:
            current_unit = label
            continue
        if not is_employee_row(row, shared):
            continue

        employee_total += 1
        row_number = int(row.get("r", "0"))
        nip = digits(cell_text(get_cell(row, "C"), shared))
        name = clean(cell_text(get_cell(row, "B"), shared))
        if current_unit not in unit_counts:
            problems.append(f"baris {row_number} {name}: unit fisik tidak diketahui")
        else:
            unit_counts[current_unit] += 1

        gender = gender_key(cell_text(get_cell(row, "AG"), shared))
        if not gender:
            problems.append(f"baris {row_number} {name}: jenis kelamin kosong/tidak dikenal")
            continue

        job_category = classify_job(
            cell_text(get_cell(row, "O"), shared),
            cell_text(get_cell(row, "P"), shared),
            cell_text(get_cell(row, "N"), shared),
        )
        job_counts[job_category][gender] += 1

        rank = normalize_rank(cell_text(get_cell(row, "J"), shared))
        if rank not in rank_counts:
            problems.append(f"baris {row_number} {name}: golongan {rank or '-'} tidak dikenal")
        else:
            rank_counts[rank][gender] += 1

        education = classify_education(
            cell_text(get_cell(row, "V"), shared),
            cell_text(get_cell(row, "W"), shared),
            cell_text(get_cell(row, "X"), shared),
            cell_text(get_cell(row, "Y"), shared),
        )
        if education not in education_counts:
            problems.append(f"baris {row_number} {name}: pendidikan tidak dapat diklasifikasikan")
        else:
            education_counts[education][gender] += 1

        status = clean(cell_text(get_cell(row, "AD"), shared)).upper()
        if status == "CPNS":
            formation_counts[101] += 1
            continue

        job = canonical_job(cell_text(get_cell(row, "O"), shared))
        # The August source abbreviates this structural title by omitting
        # "dan Kepegawaian"; it is the same formation shown on recap row 76.
        if "KEPALA SUB BAGIAN UMUM" in job:
            formation_counts[76] += 1
            continue
        matches = [
            (len(label_text), formation_row)
            for formation_row, label_text in formation_labels.items()
            if label_text and (label_text in job or job in label_text)
        ]
        if matches:
            formation_counts[max(matches)[1]] += 1
        else:
            problems.append(f"baris {row_number} {name} ({nip}): jabatan formasi tidak cocok: {job or '-'}")

    if problems:
        preview = "\n- ".join(problems[:20])
        remainder = len(problems) - min(len(problems), 20)
        suffix = f"\n... dan {remainder} masalah lain" if remainder else ""
        raise ValueError(f"Rekap PNS belum dapat dihitung:\n- {preview}{suffix}")

    return {
        "employee_total": employee_total,
        "units": unit_counts,
        "jobs": job_counts,
        "ranks": rank_counts,
        "education": education_counts,
        "formation": formation_counts,
    }


def update_recap(
    recap_root: ET.Element,
    pns_root: ET.Element,
    pppk_full_root: ET.Element,
    pppk_part_root: ET.Element,
    shared: SharedStringStore,
) -> dict[str, Any]:
    metrics = collect_pns_recap(pns_root, recap_root, shared)
    pppk_full_units = collect_unit_counts_from_sheet(pppk_full_root, shared, "K")
    pppk_part_units = collect_physical_unit_counts(pppk_part_root, shared)
    metrics["pppk_full_units"] = pppk_full_units
    metrics["pppk_part_units"] = pppk_part_units
    employee_total = metrics["employee_total"]
    pppk_full_total = sum(pppk_full_units.values())
    pppk_part_total = sum(pppk_part_units.values())

    for unit, row_number in UNIT_RECAP_ROWS.items():
        pns_count = metrics["units"][unit]
        set_numeric_cache_or_value(recap_root, f"C{row_number}", pns_count)
        full_pppk = pppk_full_units[unit]
        part_pppk = pppk_part_units[unit]
        set_numeric_cache_or_value(recap_root, f"D{row_number}", full_pppk)
        set_numeric_cache_or_value(recap_root, f"E{row_number}", part_pppk)
        set_numeric_cache_or_value(recap_root, f"F{row_number}", pns_count + full_pppk + part_pppk)
    set_numeric_cache_or_value(recap_root, "C16", employee_total)
    set_numeric_cache_or_value(recap_root, "D16", pppk_full_total)
    set_numeric_cache_or_value(recap_root, "E16", pppk_part_total)
    set_numeric_cache_or_value(recap_root, "F16", employee_total + pppk_full_total + pppk_part_total)

    for category, row_number in JOB_RECAP_ROWS.items():
        male = metrics["jobs"][category]["male"]
        female = metrics["jobs"][category]["female"]
        set_numeric_cache_or_value(recap_root, f"C{row_number}", male + female)
        set_numeric_cache_or_value(recap_root, f"E{row_number}", male)
        set_numeric_cache_or_value(recap_root, f"F{row_number}", female)
    job_male = sum(values["male"] for values in metrics["jobs"].values())
    job_female = sum(values["female"] for values in metrics["jobs"].values())
    set_numeric_cache_or_value(recap_root, "C26", employee_total)
    set_numeric_cache_or_value(recap_root, "E26", job_male)
    set_numeric_cache_or_value(recap_root, "F26", job_female)

    for rank, row_number in RANK_RECAP_ROWS.items():
        male = metrics["ranks"][rank]["male"]
        female = metrics["ranks"][rank]["female"]
        set_numeric_cache_or_value(recap_root, f"C{row_number}", male + female)
        set_numeric_cache_or_value(recap_root, f"D{row_number}", male)
        set_numeric_cache_or_value(recap_root, f"E{row_number}", female)
    set_numeric_cache_or_value(recap_root, "C46", employee_total)
    set_numeric_cache_or_value(recap_root, "D46", job_male)
    set_numeric_cache_or_value(recap_root, "E46", job_female)

    for education, row_number in EDUCATION_RECAP_ROWS.items():
        male = metrics["education"][education]["male"]
        female = metrics["education"][education]["female"]
        set_numeric_cache_or_value(recap_root, f"C{row_number}", male + female)
        set_numeric_cache_or_value(recap_root, f"D{row_number}", male)
        set_numeric_cache_or_value(recap_root, f"E{row_number}", female)
    set_numeric_cache_or_value(recap_root, "C58", employee_total)
    set_numeric_cache_or_value(recap_root, "D58", job_male)
    set_numeric_cache_or_value(recap_root, "E58", job_female)

    for row_number, count in metrics["formation"].items():
        set_numeric_cache_or_value(recap_root, f"C{row_number}", count)
        set_numeric_cache_or_value(recap_root, f"D{row_number}", count)
    set_numeric_cache_or_value(recap_root, "C102", employee_total)
    set_numeric_cache_or_value(recap_root, "D102", employee_total)
    return metrics


def validate_placements(root: ET.Element, shared: SharedStringStore) -> None:
    fitri_row = find_employee_row_by_name(root, shared, "FITRI ARUNA SIREGAR, S.SI, M.SI")
    for offset, nip in enumerate(BIDANG_4_NIPS, start=1):
        actual_row = find_employee_row_by_nip(root, shared, nip)
        if actual_row != fitri_row + offset:
            raise ValueError(f"Penempatan {nip} salah: baris {actual_row}, seharusnya {fitri_row + offset}")

    achmad_row = find_employee_row_by_nip(root, shared, ACHMAD_NIP)
    nikmal_row = find_employee_row_by_name(root, shared, "NIKMAL FAUZI LUBIS, S.T.")
    bidang_1_headers = find_unit_header_rows(root, shared, "BIDANG 1")
    bidang_2_headers = find_unit_header_rows(root, shared, "BIDANG 2")
    if len(bidang_1_headers) != 1 or len(bidang_2_headers) != 1:
        raise ValueError("Header Bidang 1/Bidang 2 tidak unik")
    if not bidang_1_headers[0] < achmad_row < bidang_2_headers[0]:
        raise ValueError(f"ACHMAD HUSEIN belum berada pada blok Bidang 1: baris {achmad_row}")
    if achmad_row != nikmal_row + 1:
        raise ValueError(
            f"ACHMAD HUSEIN belum tepat di bawah NIKMAL: {achmad_row} != {nikmal_row + 1}"
        )

    faisal_row = find_employee_row_by_name(root, shared, "FAISAL, S.E, M.M")
    irma_row = find_employee_row_by_nip(root, shared, IRMA_NIP)
    if irma_row != faisal_row + 1:
        raise ValueError(f"Penempatan IRMA salah: baris {irma_row}, seharusnya {faisal_row + 1}")


def validate_rank_updates(root: ET.Element, shared: SharedStringStore) -> None:
    for nip, expected_group in AUGUST_RANK_UPDATES.items():
        row_number = find_employee_row_by_nip(root, shared, nip)
        row = find_row(root, row_number)
        actual_group = normalize_rank(cell_text(get_cell(row, "J"), shared))
        if actual_group != expected_group:
            raise ValueError(
                f"Pangkat Agustus {nip} pada baris {row_number} masih {actual_group}, "
                f"seharusnya {expected_group}"
            )
        if nip in RANK_DETAIL_NOT_AVAILABLE:
            stale_details = [clean(cell_text(get_cell(row, column), shared)) for column in ("K", "L", "M")]
            if any(stale_details):
                raise ValueError(f"SK/TMT pangkat lama masih terbawa untuk {nip}: {stale_details}")


def validate_recap(root: ET.Element, metrics: dict[str, Any]) -> None:
    employee_total = metrics["employee_total"]
    full_total = sum(metrics["pppk_full_units"].values())
    part_total = sum(metrics["pppk_part_units"].values())
    expected = {
        "C16": employee_total,
        "D16": full_total,
        "E16": part_total,
        "F16": employee_total + full_total + part_total,
        "C26": employee_total,
        "C46": employee_total,
        "C58": employee_total,
        "C102": employee_total,
        "D102": employee_total,
    }
    expected.update({f"C{row}": metrics["units"][unit] for unit, row in UNIT_RECAP_ROWS.items()})
    expected.update({f"D{row}": metrics["pppk_full_units"][unit] for unit, row in UNIT_RECAP_ROWS.items()})
    expected.update({f"E{row}": metrics["pppk_part_units"][unit] for unit, row in UNIT_RECAP_ROWS.items()})
    expected.update(
        {
            f"F{row}": (
                metrics["units"][unit]
                + metrics["pppk_full_units"][unit]
                + metrics["pppk_part_units"][unit]
            )
            for unit, row in UNIT_RECAP_ROWS.items()
        }
    )
    expected.update(
        {
            f"C{row}": values["male"] + values["female"]
            for category, row in JOB_RECAP_ROWS.items()
            for values in [metrics["jobs"][category]]
        }
    )
    expected.update(
        {
            f"C{row}": values["male"] + values["female"]
            for rank, row in RANK_RECAP_ROWS.items()
            for values in [metrics["ranks"][rank]]
        }
    )
    expected.update(
        {
            f"C{row}": values["male"] + values["female"]
            for education, row in EDUCATION_RECAP_ROWS.items()
            for values in [metrics["education"][education]]
        }
    )
    for reference, expected_value in expected.items():
        actual = numeric_cell(root, reference)
        if actual != expected_value:
            raise ValueError(f"Rekap {reference}={actual}, seharusnya {expected_value}")


def main() -> None:
    if not SOURCE_WORKBOOK.exists():
        raise FileNotFoundError(SOURCE_WORKBOOK)
    employees = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    employee_by_nip = {digits(item.get("nip")): item for item in employees}
    required_nips = [ACHMAD_NIP] + BIDANG_4_NIPS + [IRMA_NIP]
    missing = [nip for nip in required_nips if nip not in employee_by_nip]
    if missing:
        raise ValueError(f"NIP pegawai baru tidak ada pada JSON Agustus: {missing}")
    for nip, expected_name in EXPECTED_NAMES.items():
        actual_name = clean(employee_by_nip[nip].get("namaWithGelar")).upper()
        if actual_name != expected_name:
            raise ValueError(f"Nama NIP {nip} berbeda: {actual_name!r} != {expected_name!r}")

    bidang_rows = [build_excel_row(employee_by_nip[nip]) for nip in BIDANG_4_NIPS]
    achmad_rows = [build_excel_row(employee_by_nip[ACHMAD_NIP])]
    irma_rows = [build_excel_row(employee_by_nip[IRMA_NIP])]

    with zipfile.ZipFile(SOURCE_WORKBOOK, "r") as source:
        archive_entries = {name: source.read(name) for name in source.namelist()}
        archive_info = {info.filename: info for info in source.infolist()}

    shared = SharedStringStore(archive_entries[SHARED_STRINGS])
    main_sheet = parse_sheet(archive_entries[SHEET_MAIN])
    pns_sheet = parse_sheet(archive_entries[SHEET_PNS])
    pppk_full_sheet = parse_sheet(archive_entries[SHEET_PPPK_FULL])
    pppk_part_sheet = parse_sheet(archive_entries[SHEET_PPPK_PART])
    recap_sheet = parse_sheet(archive_entries[SHEET_RECAP])

    # The row numbers below are resolved by anchor names so the update remains
    # safe if the source workbook is renamed but keeps the same content.
    fitri_main = find_employee_row_by_name(main_sheet, shared, "FITRI ARUNA SIREGAR, S.SI, M.SI")
    insert_employee_rows(main_sheet, shared, fitri_main + 1, fitri_main, bidang_rows)
    faisal_main = find_employee_row_by_name(main_sheet, shared, "FAISAL, S.E, M.M")
    insert_employee_rows(main_sheet, shared, faisal_main + 1, faisal_main, irma_rows)

    fitri_pns = find_employee_row_by_name(pns_sheet, shared, "FITRI ARUNA SIREGAR, S.SI, M.SI")
    insert_employee_rows(pns_sheet, shared, fitri_pns + 1, fitri_pns, bidang_rows)
    faisal_pns = find_employee_row_by_name(pns_sheet, shared, "FAISAL, S.E, M.M")
    insert_employee_rows(pns_sheet, shared, faisal_pns + 1, faisal_pns, irma_rows)

    # ACHMAD HUSEIN is a PNS in Bidang 1.  Use NIKMAL's white PNS row as the
    # template and place ACHMAD immediately below him, before the CPNS block.
    nikmal_main = find_employee_row_by_name(main_sheet, shared, "NIKMAL FAUZI LUBIS, S.T.")
    insert_employee_rows(main_sheet, shared, nikmal_main + 1, nikmal_main, achmad_rows)
    nikmal_pns = find_employee_row_by_name(pns_sheet, shared, "NIKMAL FAUZI LUBIS, S.T.")
    insert_employee_rows(pns_sheet, shared, nikmal_pns + 1, nikmal_pns, achmad_rows)

    # Correct two legacy NIPs by an exact-name match before the general refresh.
    for name, (old_nip, correct_nip) in NIP_CORRECTIONS.items():
        employee = employee_by_nip[correct_nip]
        if clean(employee.get("namaWithGelar")).upper() != name:
            raise ValueError(f"Nama koreksi NIP {correct_nip} berbeda: {employee.get('namaWithGelar')}")
        repair_employee_nip_by_name(main_sheet, shared, employee, old_nip, "main")
        repair_employee_nip_by_name(pppk_part_sheet, shared, employee, old_nip, "pppk_part")

    # Remove every row which is not part of the authoritative August roster.
    remove_employee_rows_by_nip(main_sheet, shared, REMOVE_FROM_MAIN)
    remove_employee_rows_by_nip(pns_sheet, shared, REMOVE_FROM_PNS)
    remove_employee_rows_by_nip(pppk_part_sheet, shared, REMOVE_FROM_PPPK_PART)

    # Refresh all rows after the roster itself is exact.
    updated_main = update_matching_employee_rows(main_sheet, shared, employee_by_nip, "main")
    updated_pns = update_matching_employee_rows(pns_sheet, shared, employee_by_nip, "pns")
    updated_pppk_full = update_matching_employee_rows(
        pppk_full_sheet, shared, employee_by_nip, "pppk_full"
    )
    updated_pppk_part = update_matching_employee_rows(
        pppk_part_sheet, shared, employee_by_nip, "pppk_part"
    )

    # The August list names these three PPPK units only at agency level, while
    # their full-time roster block places them in Bidang 4.  Write the resolved
    # August unit explicitly in both the master and full-time sheets.
    set_unit_for_nips(main_sheet, shared, PPPK_FULL_BIDANG_4_NIPS, "Q", BIDANG_4_UNIT)
    set_unit_for_nips(pppk_full_sheet, shared, PPPK_FULL_BIDANG_4_NIPS, "K", BIDANG_4_UNIT)

    main_count = recompute_numbering_and_helper(main_sheet, shared)
    pns_count = recompute_numbering_and_helper(pns_sheet, shared)
    pppk_full_count = recompute_simple_numbering(pppk_full_sheet, shared, 35)
    pppk_part_count = recompute_simple_numbering(pppk_part_sheet, shared, 27)
    if main_count != 843:
        raise ValueError(f"Jumlah baris pegawai sheet utama {main_count}, seharusnya 843")
    if pns_count != 257:
        raise ValueError(f"Jumlah baris pegawai sheet PNS {pns_count}, seharusnya 257")
    if pppk_full_count != 46 or pppk_part_count != 540:
        raise ValueError(
            f"Jumlah PPPK salah: penuh={pppk_full_count}, paruh={pppk_part_count}; "
            "seharusnya 46 dan 540"
        )

    validate_exact_rosters(
        main_sheet,
        pns_sheet,
        pppk_full_sheet,
        pppk_part_sheet,
        shared,
        employee_by_nip,
    )
    recap_metrics = update_recap(
        recap_sheet, pns_sheet, pppk_full_sheet, pppk_part_sheet, shared
    )
    validate_placements(main_sheet, shared)
    validate_placements(pns_sheet, shared)
    validate_rank_updates(main_sheet, shared)
    validate_rank_updates(pns_sheet, shared)
    validate_recap(recap_sheet, recap_metrics)

    archive_entries[SHEET_MAIN] = sheet_to_bytes(main_sheet)
    archive_entries[SHEET_PNS] = sheet_to_bytes(pns_sheet)
    archive_entries[SHEET_PPPK_FULL] = sheet_to_bytes(pppk_full_sheet)
    archive_entries[SHEET_PPPK_PART] = sheet_to_bytes(pppk_part_sheet)
    archive_entries[SHEET_RECAP] = sheet_to_bytes(recap_sheet)
    archive_entries[SHARED_STRINGS] = shared.to_bytes()

    with zipfile.ZipFile(OUTPUT_WORKBOOK, "w") as output:
        for name, data in archive_entries.items():
            output.writestr(archive_info[name], data)

    print(f"Output       : {OUTPUT_WORKBOOK.name}")
    print(f"Sheet utama : {main_count} pegawai")
    print(f"Sheet PNS   : {pns_count} pegawai")
    print(f"Sheet PPPK  : penuh={pppk_full_count}, paruh={pppk_part_count}")
    print(f"Baris update: utama={updated_main}, PNS={updated_pns}, PPPK penuh={updated_pppk_full}, PPPK paruh={updated_pppk_part}")
    print(f"Rekap PNS   : {recap_metrics['employee_total']}")
    print(f"Bidang 4    : {recap_metrics['units']['BIDANG 4']}")
    print(f"UPT 4       : {recap_metrics['units']['UPT 4']}")
    print(f"Pangkat IV/A: {sum(recap_metrics['ranks']['IV/A'].values())}")
    print(f"Total ASN   : {main_count}")


if __name__ == "__main__":
    main()
