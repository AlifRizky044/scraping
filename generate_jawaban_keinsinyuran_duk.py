#!/usr/bin/env python3
"""Generate an auditable engineering-status answer workbook from the August 2026 DUK."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter


SOURCE = Path("/Users/alif/Downloads/DUK BAPENDA KOTA MEDAN 2026 1 Agustus 2026 (2).xlsx")
OUTPUT = Path(__file__).resolve().parent / "JAWABAN FORM KEINSINYURAN - DUK BAPENDA 1 AGUSTUS 2026.xlsx"
SOURCE_SHEET = "DUK ASN BAPENDA KOTA MEDAN"

NAVY = "17365D"
BLUE = "1F4E78"
LIGHT_BLUE = "D9EAF7"
PALE_BLUE = "EAF3F8"
YELLOW = "FFF2CC"
PALE_GREEN = "E2F0D9"
PALE_RED = "FCE4D6"
WHITE = "FFFFFF"
GREY = "666666"
THIN_GREY = Side(style="thin", color="B7C9D6")

EVIDENCE_HEADERS = [
    "No.",
    "Nama Pegawai",
    "NIP",
    "Status Kepegawaian",
    "Unit Kerja",
    "Tingkat Pendidikan",
    "Jurusan",
    "Instansi Pendidikan",
    "Tanggal Ijazah",
    "Baris Sumber DUK",
]

# Pegawai tambahan yang dinyatakan masuk oleh pengguna setelah peninjauan jurusan.
USER_CONFIRMED_EQUIVALENT_NAMES = {
    "ABDUL JABBAR ZARKASYI",
}


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def digits(value: object) -> str:
    return re.sub(r"\D", "", str(value or ""))


def has_engineering_bachelor_title(name: str) -> bool:
    """Included evidence: explicit S.T./S.Tr.T., S.Kom, or S.Si title in the recorded name."""
    normalized = clean(name).upper()
    if normalized in USER_CONFIRMED_EQUIVALENT_NAMES:
        return True
    sarjana_teknik = re.search(r"(?:^|[,\s])S\.?\s*T\.?(?=$|[,\s])", normalized)
    sarjana_terapan_teknik = re.search(
        r"(?:^|[,\s])S\.?\s*TR\.?\s*T\.?(?=$|[,\s])", normalized
    )
    sarjana_komputer = re.search(r"(?:^|[,\s])S\.?\s*KOM\.?(?=$|[,\s])", normalized)
    sarjana_sains = re.search(r"(?:^|[,\s])S\.?\s*SI\.?(?=$|[,\s])", normalized)
    return bool(sarjana_teknik or sarjana_terapan_teknik or sarjana_komputer or sarjana_sains)


def qualification_basis(name: str) -> str:
    normalized = clean(name).upper()
    if normalized in USER_CONFIRMED_EQUIVALENT_NAMES:
        return "Dikonfirmasi pengguna"
    if re.search(r"(?:^|[,\s])S\.?\s*TR\.?\s*T\.?(?=$|[,\s])", normalized):
        return "S.Tr.T."
    if re.search(r"(?:^|[,\s])S\.?\s*T\.?(?=$|[,\s])", normalized):
        return "S.T./ST"
    if re.search(r"(?:^|[,\s])S\.?\s*KOM\.?(?=$|[,\s])", normalized):
        return "S.Kom"
    if re.search(r"(?:^|[,\s])S\.?\s*SI\.?(?=$|[,\s])", normalized):
        return "S.Si"
    return ""


def has_ir_title(name: str) -> bool:
    return bool(re.search(r"(?:^|[,\s])IR\.?(?=$|[,\s])", clean(name), flags=re.IGNORECASE))


def potential_technical_reason(person: dict[str, object]) -> str:
    level = clean(person["level"]).upper()
    major = clean(person["major"]).upper()
    name = clean(person["name"]).upper()

    if level == "D-IV":
        return "D-IV/Sarjana Terapan; perlu konfirmasi bahwa program studi merupakan bidang teknik"
    if any(token in name for token in ("S.KOM", "S.KOM.")) or any(
        token in major for token in ("KOMPUTER", "INFORMAT", "SISTEM INFORMASI")
    ):
        return "Bidang komputasi/informatika; perlu konfirmasi kesetaraan/kualifikasi untuk PPI"
    if any(
        token in major
        for token in (
            "SAINS",
            "MATEMAT",
            "KIMIA",
            "FISIKA",
            "BIOLOGI",
            "AGRO",
            "PERTANIAN",
            "PERKEBUNAN",
            "PERIKANAN",
            "GIZI",
        )
    ):
        return "Bidang sains/terapan; hanya dihitung jika ada bukti program penyetaraan"
    return "Jurusan tampak teknis, tetapi gelar S.T./S.Tr.T. tidak eksplisit pada DUK"


def load_people() -> list[dict[str, object]]:
    workbook = load_workbook(SOURCE, data_only=True, read_only=False)
    worksheet = workbook[SOURCE_SHEET]
    people: list[dict[str, object]] = []

    for source_row, row in enumerate(worksheet.iter_rows(min_row=7, values_only=True), start=7):
        nip = digits(row[2])
        if len(nip) < 15:
            continue
        status = clean(row[29])
        if status not in {"PNS", "CPNS", "PPPK"}:
            continue
        people.append(
            {
                "source_row": source_row,
                "name": clean(row[1]),
                "nip": nip,
                "status": status,
                "unit": clean(row[16]),
                "level": clean(row[21]),
                "major": clean(row[22]),
                "institution": clean(row[23]),
                "diploma_date": row[24],
            }
        )

    workbook.close()
    if len(people) != len({str(person["nip"]) for person in people}):
        raise ValueError("NIP duplikat ditemukan pada sheet sumber.")
    return people


def evidence_row(number: int, person: dict[str, object]) -> list[object]:
    return [
        number,
        person["name"],
        person["nip"],
        person["status"],
        person["unit"],
        person["level"],
        person["major"],
        person["institution"],
        person["diploma_date"],
        person["source_row"],
    ]


def style_summary_sheet(worksheet) -> None:
    worksheet.sheet_view.showGridLines = False
    worksheet.freeze_panes = "A7"
    worksheet.merge_cells("A1:F1")
    title = worksheet["A1"]
    title.value = "JAWABAN FORM DATA KEINSINYURAN ASN"
    title.fill = PatternFill("solid", fgColor=NAVY)
    title.font = Font(color=WHITE, bold=True, size=16)
    title.alignment = Alignment(horizontal="center", vertical="center")
    worksheet.row_dimensions[1].height = 32

    worksheet["A3"] = "Sumber DUK"
    worksheet["B3"] = SOURCE.name
    worksheet.merge_cells("B3:F3")
    worksheet["A4"] = "Sheet sumber"
    worksheet["B4"] = SOURCE_SHEET
    worksheet.merge_cells("B4:F4")
    worksheet["A5"] = "Total ASN terbaca"
    worksheet["B5"] = 843
    worksheet["D5"] = "Tanggal basis data"
    worksheet["E5"] = "1 Agustus 2026"
    worksheet.merge_cells("E5:F5")

    for row in range(3, 6):
        worksheet.cell(row, 1).font = Font(bold=True, color=NAVY)
        worksheet.cell(row, 4).font = Font(bold=True, color=NAVY)

    headers = ["No.", "Pertanyaan Form", "Jawaban", "Jumlah Bukti", "Status Dasar Data", "Catatan / Kriteria"]
    for column, header in enumerate(headers, start=1):
        cell = worksheet.cell(7, column, header)
        cell.fill = PatternFill("solid", fgColor=BLUE)
        cell.font = Font(color=WHITE, bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(top=THIN_GREY, bottom=THIN_GREY, left=THIN_GREY, right=THIN_GREY)
    worksheet.row_dimensions[7].height = 42

    widths = {"A": 7, "B": 52, "C": 14, "D": 14, "E": 25, "F": 72}
    for column, width in widths.items():
        worksheet.column_dimensions[column].width = width

    worksheet.merge_cells("A15:F15")
    caution = worksheet["A15"]
    caution.value = (
        "PENTING: angka 0 pada PPI, sertifikasi profesional, dan STRI berarti tidak teridentifikasi "
        "dari kolom DUK—bukan kepastian bahwa pegawai tersebut tidak ada. Verifikasi dokumen/PII tetap diperlukan."
    )
    caution.fill = PatternFill("solid", fgColor=YELLOW)
    caution.font = Font(bold=True, color="7F6000")
    caution.alignment = Alignment(wrap_text=True, vertical="center")
    worksheet.row_dimensions[15].height = 48

    worksheet.merge_cells("A17:F17")
    source_note = worksheet["A17"]
    source_note.value = (
        "Dasar regulasi kriteria: sarjana pendidikan bidang teknik/sarjana sains harus telah disetarakan; "
        "DUK tidak memuat bukti penyetaraan, pengalaman praktik keinsinyuran, PPI, sertifikasi, atau STRI."
    )
    source_note.font = Font(italic=True, color=GREY)
    source_note.alignment = Alignment(wrap_text=True)


def add_evidence_sheet(
    workbook: Workbook,
    title: str,
    people: list[dict[str, object]],
    note: str,
    table_name: str,
) -> None:
    worksheet = workbook.create_sheet(title)
    worksheet.sheet_view.showGridLines = False
    worksheet["A1"] = "Jumlah pegawai teridentifikasi"
    worksheet["B1"] = len(people)
    worksheet["A1"].font = Font(bold=True, color=NAVY)
    worksheet["B1"].font = Font(bold=True, color=NAVY, size=14)
    worksheet.merge_cells("C1:J1")
    worksheet["C1"] = note
    worksheet["C1"].fill = PatternFill("solid", fgColor=YELLOW if not people else PALE_BLUE)
    worksheet["C1"].alignment = Alignment(wrap_text=True, vertical="center")
    worksheet.row_dimensions[1].height = 42

    header_row = 4
    for column, header in enumerate(EVIDENCE_HEADERS, start=1):
        cell = worksheet.cell(header_row, column, header)
        cell.fill = PatternFill("solid", fgColor=BLUE)
        cell.font = Font(color=WHITE, bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(top=THIN_GREY, bottom=THIN_GREY, left=THIN_GREY, right=THIN_GREY)
    worksheet.row_dimensions[header_row].height = 38

    for number, person in enumerate(people, start=1):
        row_number = header_row + number
        for column, value in enumerate(evidence_row(number, person), start=1):
            cell = worksheet.cell(row_number, column, value)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(bottom=Side(style="hair", color="D9E2F3"))
            if row_number % 2 == 0:
                cell.fill = PatternFill("solid", fgColor="F7FBFD")
        worksheet.cell(row_number, 3).number_format = "@"

    last_row = header_row + max(len(people), 1)
    worksheet.auto_filter.ref = f"A{header_row}:J{last_row}"
    worksheet.freeze_panes = "A5"
    widths = [7, 40, 22, 20, 60, 22, 32, 44, 20, 18]
    for column, width in enumerate(widths, start=1):
        worksheet.column_dimensions[get_column_letter(column)].width = width

    if people:
        table = Table(displayName=table_name, ref=f"A{header_row}:J{header_row + len(people)}")
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2", showFirstColumn=False, showLastColumn=False, showRowStripes=True
        )
        worksheet.add_table(table)
    else:
        worksheet.merge_cells("A5:J5")
        worksheet["A5"] = "Tidak ada pegawai yang dapat dibuktikan masuk kategori ini dari data DUK."
        worksheet["A5"].fill = PatternFill("solid", fgColor=PALE_RED)
        worksheet["A5"].alignment = Alignment(wrap_text=True)

    worksheet.sheet_properties.pageSetUpPr.fitToPage = True
    worksheet.page_setup.fitToWidth = 1
    worksheet.page_setup.fitToHeight = 0
    worksheet.print_title_rows = "4:4"


def add_candidate_sheet(workbook: Workbook, candidates: list[dict[str, object]]) -> None:
    worksheet = workbook.create_sheet("KANDIDAT VERIFIKASI")
    worksheet.sheet_view.showGridLines = False
    worksheet["A1"] = "Kandidat belum dihitung sebagai lulusan teknik"
    worksheet["B1"] = len(candidates)
    worksheet["A1"].font = Font(bold=True, color=NAVY)
    worksheet["B1"].font = Font(bold=True, color=NAVY, size=14)
    worksheet.merge_cells("C1:K1")
    worksheet["C1"] = (
        "Nama pada sheet ini memiliki jurusan yang tampak teknis/sains/terapan, tetapi bukti gelar teknik atau "
        "penyetaraan tidak cukup eksplisit di DUK. Jangan tambahkan ke jawaban sebelum verifikasi ijazah/penyetaraan."
    )
    worksheet["C1"].fill = PatternFill("solid", fgColor=YELLOW)
    worksheet["C1"].alignment = Alignment(wrap_text=True, vertical="center")
    worksheet.row_dimensions[1].height = 48

    headers = EVIDENCE_HEADERS + ["Alasan Perlu Verifikasi"]
    for column, header in enumerate(headers, start=1):
        cell = worksheet.cell(4, column, header)
        cell.fill = PatternFill("solid", fgColor=BLUE)
        cell.font = Font(color=WHITE, bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for number, person in enumerate(candidates, start=1):
        row_number = 4 + number
        values = evidence_row(number, person) + [potential_technical_reason(person)]
        for column, value in enumerate(values, start=1):
            cell = worksheet.cell(row_number, column, value)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        worksheet.cell(row_number, 3).number_format = "@"

    last_row = 4 + len(candidates)
    worksheet.auto_filter.ref = f"A4:K{last_row}"
    worksheet.freeze_panes = "A5"
    widths = [7, 40, 22, 20, 60, 22, 32, 44, 20, 18, 58]
    for column, width in enumerate(widths, start=1):
        worksheet.column_dimensions[get_column_letter(column)].width = width
    table = Table(displayName="TabelKandidatVerifikasi", ref=f"A4:K{last_row}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    worksheet.add_table(table)


def add_methodology_sheet(
    workbook: Workbook,
    people: list[dict[str, object]],
    s1_plus: list[dict[str, object]],
    engineering: list[dict[str, object]],
    candidates: list[dict[str, object]],
) -> None:
    worksheet = workbook.create_sheet("METODOLOGI")
    worksheet.sheet_view.showGridLines = False
    worksheet.merge_cells("A1:D1")
    worksheet["A1"] = "METODOLOGI, ASUMSI, DAN KONTROL HITUNG"
    worksheet["A1"].fill = PatternFill("solid", fgColor=NAVY)
    worksheet["A1"].font = Font(color=WHITE, bold=True, size=15)
    worksheet["A1"].alignment = Alignment(horizontal="center")

    rows = [
        ("Cakupan ASN", "Semua baris dengan NIP valid dan status PNS, CPNS, atau PPPK pada sheet utama; outsourcing dikecualikan."),
        ("ASN Strata-1 ke atas", "S1, S2, S3, dan D-IV. D-IV dimasukkan sebagai jenjang setara sarjana. Jika form harus dimaknai literal hanya S1/S2/S3, gunakan 605 (bukan 615)."),
        ("Lulusan teknik/sains", "Nama memuat gelar S.T./ST, S.Tr.T., S.Kom, atau S.Si secara eksplisit. Gelar S.STP/SSTP tidak dianggap S.T."),
        ("Asumsi penyetaraan", "S.Kom dan S.Si dimasukkan sebagai sarjana sains/komputasi. Abdul Jabbar Zarkasyi juga dimasukkan karena jurusan Teknik Sipil, sesuai konfirmasi pengguna."),
        ("Sedang PPI", "DUK tidak memiliki kolom/status sedang mengikuti Program Profesi Insinyur."),
        ("Gelar Ir.", "Dicari sebagai token gelar Ir. pada nama, bukan sebagai potongan kata lain."),
        ("Sertifikasi profesional/STRI", "DUK tidak memiliki nomor/status sertifikasi insinyur profesional maupun STRI."),
        ("Makna angka 0", "0 teridentifikasi dari DUK; harus diverifikasi lagi terhadap ijazah profesi, data PII, dan dokumen STRI."),
    ]
    worksheet["A3"] = "Aspek"
    worksheet["B3"] = "Kriteria"
    worksheet["A3"].fill = worksheet["B3"].fill = PatternFill("solid", fgColor=BLUE)
    worksheet["A3"].font = worksheet["B3"].font = Font(color=WHITE, bold=True)
    for row_number, (aspect, criterion) in enumerate(rows, start=4):
        worksheet.cell(row_number, 1, aspect).font = Font(bold=True, color=NAVY)
        worksheet.cell(row_number, 2, criterion).alignment = Alignment(wrap_text=True, vertical="top")
        worksheet.row_dimensions[row_number].height = 42

    counts = Counter(clean(person["status"]) for person in people)
    level_counts = Counter(clean(person["level"]) for person in people)
    controls = [
        ("Total ASN", len(people)),
        ("PNS", counts["PNS"]),
        ("CPNS", counts["CPNS"]),
        ("PPPK", counts["PPPK"]),
        ("S1", level_counts["S1 (Sarjana)"]),
        ("S2", level_counts["S2 (Magister)"]),
        ("S3", level_counts["S3 (Doktor)"]),
        ("D-IV", level_counts["D-IV"]),
        ("S1 ke atas termasuk D-IV", len(s1_plus)),
        ("Teknik/sains yang dimasukkan", len(engineering)),
        ("Kandidat perlu verifikasi", len(candidates)),
    ]
    worksheet["D3"] = "Kontrol"
    worksheet["E3"] = "Jumlah"
    worksheet["D3"].fill = worksheet["E3"].fill = PatternFill("solid", fgColor=BLUE)
    worksheet["D3"].font = worksheet["E3"].font = Font(color=WHITE, bold=True)
    for row_number, (label, value) in enumerate(controls, start=4):
        worksheet.cell(row_number, 4, label)
        worksheet.cell(row_number, 5, value)

    worksheet.column_dimensions["A"].width = 31
    worksheet.column_dimensions["B"].width = 105
    worksheet.column_dimensions["C"].width = 4
    worksheet.column_dimensions["D"].width = 34
    worksheet.column_dimensions["E"].width = 14
    worksheet.freeze_panes = "A4"


def main() -> None:
    people = load_people()
    if len(people) != 843:
        raise ValueError(f"Kontrol total ASN gagal: terbaca {len(people)}, diharapkan 843.")

    bachelor_equivalent_levels = {"S1 (Sarjana)", "S2 (Magister)", "S3 (Doktor)", "D-IV"}
    s1_plus = [person for person in people if clean(person["level"]) in bachelor_equivalent_levels]
    engineering = [person for person in people if has_engineering_bachelor_title(clean(person["name"]))]
    ir_holders = [person for person in people if has_ir_title(clean(person["name"]))]

    candidate_pattern = re.compile(
        r"TEKNIK|TEKNOLOG|KOMPUTER|INFORMAT|SISTEM INFORMASI|SISTEM KOMPUTER|SAINS|MATEMAT|KIMIA|FISIKA|BIOLOGI|AGRO|PERTANIAN|PERKEBUNAN|PERIKANAN|GIZI|PABRIK|PLANOLOGI|PERENCANAAN WILAYAH",
        flags=re.IGNORECASE,
    )
    candidates = [
        person
        for person in people
        if clean(person["level"]) in bachelor_equivalent_levels
        and not has_engineering_bachelor_title(clean(person["name"]))
        and candidate_pattern.search(clean(person["major"]))
    ]

    for collection in (s1_plus, engineering, ir_holders, candidates):
        collection.sort(key=lambda person: (clean(person["status"]), clean(person["name"])))

    workbook = Workbook()
    summary = workbook.active
    summary.title = "RINGKASAN"
    style_summary_sheet(summary)

    questions = [
        (
            1,
            "Jumlah ASN Strata-1 ke atas",
            len(s1_plus),
            len(s1_plus),
            "Terbukti dari pendidikan DUK",
            "Mencakup S1 (538), S2 (66), S3 (1), dan D-IV (10). Jika D-IV tidak dimasukkan, jawabannya 605.",
        ),
        (
            2,
            "Jumlah Lulusan Sarjana Bidang Teknik / Sarjana Terapan Bidang Teknik / Sarjana Pendidikan Bidang Teknik / Sarjana Sains yang disetarakan",
            len(engineering),
            len(engineering),
            "Gelar eksplisit pada nama",
            "Mencakup S.T./ST (31), S.Kom (34), S.Si (3), dan Abdul Jabbar Zarkasyi (Teknik Sipil). "
            f"Ada {len(candidates)} kandidat lain yang masih perlu verifikasi ijazah/penyetaraan.",
        ),
        (
            3,
            "Jumlah sedang mengikuti/menjalani Program Profesi Insinyur (PPI)",
            0,
            0,
            "Tidak tersedia di DUK",
            "0 teridentifikasi; perlu konfirmasi kepegawaian/pegawai secara terpisah.",
        ),
        (
            4,
            "Jumlah telah memiliki Gelar Insinyur (Ir.)",
            len(ir_holders),
            len(ir_holders),
            "Pencarian gelar pada nama",
            "Tidak ditemukan token gelar Ir. pada nama pegawai di DUK.",
        ),
        (
            5,
            "Jumlah telah bergelar Insinyur (Ir.) dan dalam proses Sertifikasi Insinyur Profesional",
            0,
            0,
            "Tidak tersedia di DUK",
            "Tidak ada pemegang gelar Ir. yang teridentifikasi; status proses sertifikasi juga tidak dicatat.",
        ),
        (
            6,
            "Jumlah Pemegang Surat Tanda Registrasi Insinyur (STRI)",
            0,
            0,
            "Tidak tersedia di DUK",
            "DUK tidak memuat nomor/status STRI; 0 berarti tidak teridentifikasi.",
        ),
    ]
    for row_number, values in enumerate(questions, start=8):
        for column, value in enumerate(values, start=1):
            cell = summary.cell(row_number, column, value)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(top=THIN_GREY, bottom=THIN_GREY, left=THIN_GREY, right=THIN_GREY)
            if row_number % 2 == 0:
                cell.fill = PatternFill("solid", fgColor=PALE_BLUE)
        summary.cell(row_number, 3).font = Font(bold=True, size=14, color=NAVY)
        summary.cell(row_number, 3).alignment = Alignment(horizontal="center", vertical="center")
        summary.cell(row_number, 4).alignment = Alignment(horizontal="center", vertical="center")
        summary.row_dimensions[row_number].height = 68

    add_evidence_sheet(
        workbook,
        "BUKTI ASN S1+",
        s1_plus,
        "Daftar ASN S1/S2/S3/D-IV yang membentuk jawaban No. 1.",
        "TabelBuktiAsnS1Plus",
    )
    add_evidence_sheet(
        workbook,
        "BUKTI LULUSAN TEKNIK",
        engineering,
        "Daftar pegawai dengan gelar S.T./ST/S.Tr.T., S.Kom, S.Si, serta Abdul Jabbar Zarkasyi (Teknik Sipil) untuk jawaban No. 2.",
        "TabelBuktiLulusanTeknik",
    )
    add_evidence_sheet(
        workbook,
        "BUKTI SEDANG PPI",
        [],
        "DUK tidak mempunyai kolom/status sedang mengikuti Program Profesi Insinyur.",
        "TabelBuktiSedangPpi",
    )
    add_evidence_sheet(
        workbook,
        "BUKTI GELAR IR",
        ir_holders,
        "Dicari sebagai token gelar Ir. pada nama pegawai.",
        "TabelBuktiGelarIr",
    )
    add_evidence_sheet(
        workbook,
        "BUKTI IR + SERTIF",
        [],
        "DUK tidak mencatat proses Sertifikasi Insinyur Profesional.",
        "TabelBuktiIrSertif",
    )
    add_evidence_sheet(
        workbook,
        "BUKTI STRI",
        [],
        "DUK tidak mempunyai kolom nomor/status Surat Tanda Registrasi Insinyur (STRI).",
        "TabelBuktiStri",
    )
    add_candidate_sheet(workbook, candidates)
    add_methodology_sheet(workbook, people, s1_plus, engineering, candidates)

    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.calculation.calcMode = "auto"
    workbook.save(OUTPUT)
    print(f"Created: {OUTPUT}")
    print(f"ASN: {len(people)} | S1+: {len(s1_plus)} | Teknik: {len(engineering)} | Ir.: {len(ir_holders)}")
    print(f"Kandidat verifikasi: {len(candidates)} | Waktu: {datetime.now().isoformat(timespec='seconds')}")


if __name__ == "__main__":
    main()
