#!/usr/bin/env python3
"""Menyusun rekap pegawai Bapenda per 31 Desember 2025.

Sumber utama:
- DUK Excel sekitar Oktober 2025.
- Snapshot JSON sesudah akhir 2025.

Metode sengaja menyimpan jejak koreksi dan bukti kualifikasi di workbook
keluaran agar angka hasil rekonsiliasi dapat diaudit kembali.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".codex_deps"))

from openpyxl import Workbook, load_workbook  # noqa: E402
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # noqa: E402
from openpyxl.worksheet.table import Table, TableStyleInfo  # noqa: E402


EXCEL_SOURCE = Path("/Users/alif/Downloads/duk 2025.xlsx")
JSON_SOURCE = ROOT / "DUKPNSFULLOLD.json"
OUTPUT = ROOT / "Rekap_Pegawai_per_31_Desember_2025.xlsx"
AS_OF = date(2025, 12, 31)

# Ketiga pegawai ini muncul di JSON, tetapi riwayat jabatan menunjukkan bahwa
# mereka baru masuk Bapenda setelah tanggal potong laporan.
POST_CUTOFF_NIPS = {
    "198106032015052001": "Mutasi ke Bapenda efektif 01-01-2026",
    "198306252010011026": "Mutasi ke Bapenda efektif 01-02-2026",
    "199909152022082001": "Mutasi ke Bapenda efektif 01-02-2026",
}

# Pegawai ini ada di DUK Oktober, tidak ada di JSON pasca-2025 karena BUP-nya
# tepat 1 Januari 2026. Ia masih termasuk pada 31 Desember 2025.
RETAIN_FROM_EXCEL_NIP = "196712031993031004"

# Pegawai ini masih ada pada DUK Oktober, tetapi BUP 1 November 2025 dan sudah
# tidak ada di JSON. Dengan memakai JSON sebagai basis ASN, ia otomatis tidak
# masuk ke hasil akhir.
RETIRED_2025_NIP = "196710041991031003"


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def digits(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    raw = str(value).strip()
    if re.fullmatch(r"\d+", raw):
        return raw
    if re.fullmatch(r"\d+\.0", raw):
        return raw[:-2]
    if re.fullmatch(r"\d(?:\.\d+)?[Ee]\+?\d+", raw):
        try:
            return str(int(float(raw)))
        except ValueError:
            return ""
    return re.sub(r"\D", "", raw)


def normalize_name(value: Any) -> str:
    raw = unicodedata.normalize("NFKD", text(value))
    raw = raw.encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]", "", raw)


def parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = text(value)
    if not raw or raw in {"0000-00-00", "00-00-0000"}:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            pass
    return None


def dob_from_nip(nip: str) -> date | None:
    if not re.fullmatch(r"\d{18}", nip):
        return None
    try:
        return datetime.strptime(nip[:8], "%Y%m%d").date()
    except ValueError:
        return None


def start_from_nip(nip: str, status: str) -> date | None:
    if not re.fullmatch(r"\d{18}", nip):
        return None
    if status == "PPPK":
        # NIP PPPK sumber ini berkode tahun pengangkatan 2025; dua digit
        # sesudah tahun adalah kode jenis kelamin, bukan bulan.
        try:
            return date(int(nip[8:12]), 1, 1)
        except ValueError:
            return None
    try:
        return date(int(nip[8:12]), int(nip[12:14]), 1)
    except ValueError:
        return None


def completed_years(start: date | None, end: date) -> int | None:
    if start is None or start > end:
        return None
    return end.year - start.year - ((end.month, end.day) < (start.month, start.day))


def age_on(dob: date | None, ref: date) -> int | None:
    return completed_years(dob, ref)


def education_rank(raw: Any) -> tuple[int, str]:
    s = text(raw).upper().replace("–", "-")
    compact = re.sub(r"[^A-Z0-9]", "", s)
    if not s:
        return 0, "Tidak diketahui"
    if "S3" in compact or "DOKTOR" in s:
        return 9, "S3"
    if "S2" in compact or "MAGISTER" in s:
        return 8, "S2"
    if "D4" in compact or "DIV" in compact:
        return 7, "D4/S1"
    if "S1" in compact or "SARJANA" in s:
        return 7, "D4/S1"
    if "D3" in compact or "DIII" in compact:
        return 6, "D3"
    if "D2" in compact or "DII" in compact:
        return 5, "D2"
    if "D1" in compact or compact == "DI":
        return 4, "D1"
    if any(k in s for k in ("SMA", "SMK", "SLTA", "SMU", "STM", "MA ", "PAKET C")) or s == "MA":
        return 3, "SMA/sederajat"
    if "SMP" in s or "MTS" in s:
        return 2, "SMP/sederajat"
    if s == "SD" or "SEKOLAH DASAR" in s:
        return 1, "SD"
    return 0, "Tidak diketahui"


def highest_education(history: Any) -> tuple[str, str]:
    if not isinstance(history, list):
        return "Tidak diketahui", ""
    best_rank = -1
    best_label = "Tidak diketahui"
    best_detail = ""
    for item in history:
        if not isinstance(item, dict):
            continue
        raw = item.get("tingkatPendidikan") or item.get("detailPendidikan") or ""
        rank, label = education_rank(raw)
        if rank > best_rank:
            best_rank = rank
            best_label = label
            best_detail = text(item.get("detailPendidikan") or raw)
    return best_label, best_detail


def add_table(ws, start_row: int, end_row: int, end_col: int, name: str) -> None:
    if end_row <= start_row:
        return
    from openpyxl.utils import get_column_letter

    ref = f"A{start_row}:{get_column_letter(end_col)}{end_row}"
    table = Table(displayName=name, ref=ref)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    ws.add_table(table)


def apply_sheet_style(ws, widths: dict[str, float], freeze: str | None = None) -> None:
    for col, width in widths.items():
        ws.column_dimensions[col].width = width
    if freeze:
        ws.freeze_panes = freeze
    ws.sheet_view.showGridLines = False
    ws.auto_filter.ref = ws.dimensions


def make_title(ws, title: str, subtitle: str, end_col: int) -> None:
    from openpyxl.utils import get_column_letter

    end = get_column_letter(end_col)
    ws.merge_cells(f"A1:{end}1")
    ws["A1"] = title
    ws["A1"].font = Font(size=16, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor="17365D")
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 28
    ws.merge_cells(f"A2:{end}2")
    ws["A2"] = subtitle
    ws["A2"].font = Font(size=10, italic=True, color="44546A")
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[2].height = 32


def extract_excel_sources(path: Path) -> dict[str, Any]:
    wb = load_workbook(path, data_only=True, read_only=True)
    ws_main = wb["DUK PNS SESUAI UNIT KERJA OKTOB"]
    ws_pppk = wb["DUK PPPK BAPENDA"]
    ws_phl = wb["DAFTAR NAMA PHL BAPENDA+OS"]
    ws_rekap_phl = wb["REKAPITULASI PHL "]
    ws_rekap_all = wb["Copy of REKAPITULASI PHL "]

    main_by_nip: dict[str, dict[str, Any]] = {}
    for row in ws_main.iter_rows(min_row=7, values_only=True):
        nip = digits(row[2])
        if len(nip) != 18:
            continue
        main_by_nip[nip] = {
            "nama": text(row[1]),
            "nip": nip,
            "masa_tahun_2024": row[3],
            "masa_bulan_2024": row[4],
            "jabatan": text(row[14]),
            "unit": text(row[16]),
            "pendidikan": text(row[21]),
            "bup": row[26],
            "status": text(row[29]),
        }

    pppk_nips: set[str] = set()
    pppk_edu_by_nip: dict[str, str] = {}
    for row in ws_pppk.iter_rows(min_row=3, values_only=True):
        nip = digits(row[2])
        if len(nip) != 18:
            continue
        pppk_nips.add(nip)
        pppk_edu_by_nip[nip] = text(row[29])  # kolom AD

    phl_records: list[dict[str, Any]] = []
    phl_edu_by_nik: dict[str, str] = {}
    for row_num, row in enumerate(
        ws_phl.iter_rows(min_row=5, max_row=606, values_only=True), start=5
    ):
        name = text(row[1])
        if not name or name.upper() == "NAMA UNOR":
            continue
        nik = digits(row[2])
        record = {
            "row": row_num,
            "nama": name,
            "nik": nik,
            "tempat_lahir": text(row[3]),
            "tanggal_lahir": row[4],
            "jenis_kelamin": text(row[5]),
            "pendidikan": text(row[6]),
            "program_studi": text(row[7]),
            "tmt_pertama": row[8],
            "unit": text(row[9]),
            "jenis_jabatan": text(row[11]),
            "jabatan_kontrak": text(row[12]),
            "status_seleksi": text(row[13]),
        }
        phl_records.append(record)
        if len(nik) == 16 and record["pendidikan"]:
            phl_edu_by_nik[nik] = record["pendidikan"]

    # Angka rekap eksplisit dari workbook sumber.
    phl_count = int(ws_rekap_phl["C19"].value)
    total_phl_os = int(ws_rekap_all["C19"].value)
    outsourcing_count = int(ws_rekap_all["G19"].value)

    return {
        "main_by_nip": main_by_nip,
        "pppk_nips": pppk_nips,
        "pppk_edu_by_nip": pppk_edu_by_nip,
        "phl_records": phl_records,
        "phl_edu_by_nik": phl_edu_by_nik,
        "phl_count": phl_count,
        "total_phl_os": total_phl_os,
        "outsourcing_count": outsourcing_count,
    }


def evidence_year(entry: dict[str, Any]) -> int | None:
    d = parse_date(entry.get("tmt") or entry.get("mulai"))
    if d:
        return d.year
    raw = text(entry.get("anggaran"))
    return int(raw) if re.fullmatch(r"20\d{2}", raw) else None


def bapenda_context(value: str) -> bool:
    s = value.upper()
    return "PENDAPATAN" in s or "PAJAK DAN RETRIBUSI" in s


def collect_qualification_evidence(
    roster: list[dict[str, Any]], phl_records: list[dict[str, Any]]
) -> tuple[dict[str, set[str]], list[dict[str, str]]]:
    categories: dict[str, set[str]] = defaultdict(set)
    rows: list[dict[str, str]] = []

    def register(category: str, key: str, person: dict[str, Any], kind: str, ev: str, when: str) -> None:
        categories[category].add(key)
        rows.append(
            {
                "kategori": category,
                "nip": text(person.get("nip")),
                "nik": text(person.get("nik")),
                "nama": text(person.get("nama")),
                "jenis_bukti": kind,
                "bukti": ev,
                "tanggal_tahun": when,
            }
        )

    for person in roster:
        nip = text(person.get("nip"))
        key = f"NIP:{nip}"
        current_job = text(person.get("jabatanTerakhir"))
        if re.search(r"ANALIS SUMBER DAYA MANUSIA APARATUR", current_job, re.I):
            register("Administrasi Kepegawaian", key, person, "Jabatan terakhir", current_job, "31-12-2025")

        history = person.get("riwayatJabatan")
        if isinstance(history, list):
            for item in history:
                if not isinstance(item, dict):
                    continue
                job = text(item.get("jabatan"))
                unit = text(item.get("skpd"))
                yr = evidence_year(item)
                when = text(item.get("tmt"))
                recent_bapenda = bapenda_context(unit) and (yr is None or yr >= 2020)
                combined = f"{job} | {unit}"
                if recent_bapenda and re.search(r"PEMERIKS(?:A|AAN).*PAJAK", job, re.I):
                    register("Pemeriksa Pajak", key, person, "Riwayat jabatan relevan", combined, when)
                if recent_bapenda and re.search(r"JURU\s*SITA|JURUSITA", job, re.I):
                    register("Juru Sita Pajak", key, person, "Riwayat jabatan relevan", combined, when)
                if recent_bapenda and re.search(r"PENAGIH", combined, re.I):
                    register("Penagihan Pajak", key, person, "Riwayat jabatan relevan", combined, when)
                if recent_bapenda and re.search(r"PENDATA", job, re.I) and re.search(
                    r"PAJAK|WAJIB|OBJEK|PENDAFTARAN|RETRIBUSI", job, re.I
                ):
                    register("Pendata Pajak", key, person, "Riwayat jabatan relevan", combined, when)
                if recent_bapenda and re.search(r"PENILAI", job, re.I) and re.search(
                    r"PBB|PAJAK BUMI|BANGUNAN", combined, re.I
                ):
                    register("Penilai PBB-P2", key, person, "Riwayat jabatan relevan", combined, when)
                if recent_bapenda and re.search(
                    r"PRANATA KOMPUTER|TEKNOLOGI INFORMASI|SISTEM INFORMASI|SISTEM PERPAJAKAN|PENGELOLA SISTEM|PENATA KELOLA SISTEM",
                    job,
                    re.I,
                ):
                    register("IT/Sistem Perpajakan", key, person, "Riwayat jabatan relevan", combined, when)
                if recent_bapenda and re.search(r"PENYIDIK", job, re.I):
                    register("Penyidikan", key, person, "Riwayat jabatan relevan", combined, when)
                if recent_bapenda and re.search(
                    r"ANALIS KEPEGAWAIAN|SUMBER DAYA MANUSIA APARATUR", job, re.I
                ):
                    register("Administrasi Kepegawaian", key, person, "Riwayat jabatan relevan", combined, when)

        training = person.get("riwayatDiklatLainnya")
        if isinstance(training, list):
            for item in training:
                if not isinstance(item, dict):
                    continue
                name = text(item.get("namaDiklat"))
                when = text(item.get("mulai") or item.get("anggaran"))
                if re.search(r"PEMERIKS(?:A|AAN).*PAJAK", name, re.I):
                    register("Pemeriksa Pajak", key, person, "Diklat/sertifikasi", name, when)
                if re.search(r"JURU\s*SITA|JURUSITA", name, re.I) and "PAJAK" in name.upper():
                    register("Juru Sita Pajak", key, person, "Diklat/sertifikasi", name, when)
                if re.search(r"PENILAI", name, re.I) and re.search(
                    r"PBB|PAJAK BUMI|BANGUNAN", name, re.I
                ):
                    register("Penilai PBB-P2", key, person, "Diklat/sertifikasi", name, when)
                if re.search(r"SISTEM INFORMASI PAJAK DAERAH|\bSIPDA\b", name, re.I):
                    register("IT/Sistem Perpajakan", key, person, "Diklat/sertifikasi", name, when)
                if re.search(r"PENYIDIK", name, re.I):
                    register("Penyidikan", key, person, "Diklat/sertifikasi", name, when)
                if re.search(
                    r"ANALIS KEPEGAWAIAN KEAHLIAN|ANALIS SUMBER DAYA MANUSIA APARATUR", name, re.I
                ):
                    register("Administrasi Kepegawaian", key, person, "Diklat/sertifikasi", name, when)

    # Tambahkan bukti peran eksplisit dari daftar kontrak 2025. Hanya jabatan
    # yang sangat spesifik dipakai; jabatan umum tidak ditebak.
    for person in phl_records:
        job = text(person.get("jabatan_kontrak"))
        if "OPERATOR KOMPUTER" not in job.upper():
            continue
        nik = text(person.get("nik"))
        key = f"NIK:{nik}" if len(nik) == 16 else f"NAMA:{normalize_name(person.get('nama'))}"
        register(
            "IT/Sistem Perpajakan",
            key,
            person,
            "Jabatan kontrak 2025",
            f"{job} | {text(person.get('unit'))}",
            "2025",
        )

    # Hilangkan duplikasi bukti persis yang sering muncul dua kali di JSON.
    dedup: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    for row in rows:
        sig = tuple(row[k] for k in ("kategori", "nip", "nik", "nama", "jenis_bukti", "bukti", "tanggal_tahun"))
        if sig not in seen:
            seen.add(sig)
            dedup.append(row)
    return categories, dedup


def build_roster(json_rows: list[dict[str, Any]], excel: dict[str, Any]) -> list[dict[str, Any]]:
    roster = [r.copy() for r in json_rows if text(r.get("nip")) not in POST_CUTOFF_NIPS]
    existing = {text(r.get("nip")) for r in roster}
    assert RETAIN_FROM_EXCEL_NIP not in existing

    source = excel["main_by_nip"][RETAIN_FROM_EXCEL_NIP]
    roster.append(
        {
            "nip": RETAIN_FROM_EXCEL_NIP,
            "nik": "",
            "nama": source["nama"],
            "namaWithGelar": source["nama"],
            "statusKepegawaian": source["status"] or "PNS",
            "kedudukanKepegawaian": "Aktif per 31-12-2025; BUP 01-01-2026",
            "jabatanTerakhir": source["jabatan"],
            "skpd": source["unit"],
            "tanggalLahir": dob_from_nip(RETAIN_FROM_EXCEL_NIP).isoformat(),
            "riwayatPendidikan": "",
            "riwayatPangkat": "",
            "riwayatJabatan": "",
            "riwayatDiklatLainnya": "",
            "riwayatDiklatStruktural": "",
            "_education_fallback": source["pendidikan"],
            "_source": "DUK Oktober 2025 (dipertahankan karena BUP 01-01-2026)",
        }
    )
    assert len(roster) == 848, f"Roster ASN hasil rekonsiliasi bukan 848, melainkan {len(roster)}"
    return roster


def enrich_roster(roster: list[dict[str, Any]], excel: dict[str, Any]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for r in roster:
        item = r.copy()
        nip = text(item.get("nip"))
        nik = digits(item.get("nik"))
        status = text(item.get("statusKepegawaian"))

        dob = parse_date(item.get("tanggalLahir")) or dob_from_nip(nip)
        age = age_on(dob, AS_OF)

        edu_label, edu_detail = highest_education(item.get("riwayatPendidikan"))
        if edu_label == "Tidak diketahui":
            raw = text(item.get("_education_fallback"))
            if not raw:
                raw = text(excel["main_by_nip"].get(nip, {}).get("pendidikan"))
            if not raw:
                raw = text(excel["pppk_edu_by_nip"].get(nip))
            if not raw and len(nik) == 16:
                raw = text(excel["phl_edu_by_nik"].get(nik))
            if raw:
                _, edu_label = education_rank(raw)
                edu_detail = raw

        start = None
        history = item.get("riwayatPangkat")
        if isinstance(history, list):
            dates = [parse_date(x.get("tmt")) for x in history if isinstance(x, dict)]
            dates = [d for d in dates if d]
            if dates:
                start = min(dates)
        if start is None:
            start = start_from_nip(nip, status)
        tenure = completed_years(start, AS_OF)

        item.update(
            {
                "_dob": dob,
                "_age": age,
                "_edu_label": edu_label,
                "_edu_detail": edu_detail,
                "_start": start,
                "_tenure": tenure,
                "_source": text(item.get("_source")) or "DUKPNSFULLOLD.json (dikoreksi tanggal efektif)",
            }
        )
        enriched.append(item)
    return sorted(enriched, key=lambda x: (text(x.get("statusKepegawaian")), text(x.get("nama"))))


def group_counts(roster: list[dict[str, Any]]) -> dict[str, Counter]:
    status = Counter(text(r.get("statusKepegawaian")) for r in roster)
    edu = Counter(text(r.get("_edu_label")) for r in roster)
    age = Counter()
    tenure = Counter()
    for r in roster:
        a = r.get("_age")
        if a is None:
            age["Tidak diketahui"] += 1
        elif a <= 30:
            age["<=30"] += 1
        elif a <= 45:
            age["31-45"] += 1
        else:
            age[">45"] += 1

        t = r.get("_tenure")
        if t is None:
            tenure["Tidak diketahui"] += 1
        elif t <= 10:
            tenure["0-10"] += 1
        elif t <= 20:
            tenure["11-20"] += 1
        elif t <= 30:
            tenure["21-30"] += 1
        else:
            tenure[">30"] += 1
    return {"status": status, "education": edu, "age": age, "tenure": tenure}


def write_workbook(
    roster: list[dict[str, Any]],
    excel: dict[str, Any],
    qualification_counts: dict[str, set[str]],
    qualification_evidence: list[dict[str, str]],
) -> None:
    counts = group_counts(roster)
    total_asn = len(roster)
    outsourcing = excel["outsourcing_count"]
    total_workforce = total_asn + outsourcing

    wb = Workbook()
    ws = wb.active
    ws.title = "REKAP 31-12-2025"
    make_title(
        ws,
        "REKAP SDM & ORGANISASI — POSISI 31 DESEMBER 2025",
        "Hasil rekonsiliasi DUK Oktober 2025 dengan snapshot JSON pasca-2025. Angka kompetensi adalah minimum teridentifikasi dari jabatan, riwayat jabatan, dan diklat; data anggaran/penghasilan serta KI & transparansi tidak tersedia pada sumber.",
        6,
    )
    headers = ["No.", "Parameter", "Nilai", "Status Data", "Dasar Perhitungan", "Catatan"]
    for col, value in enumerate(headers, 1):
        cell = ws.cell(4, col, value)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4472C4")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    q = lambda name: len(qualification_counts.get(name, set()))
    education = counts["education"]
    age = counts["age"]
    tenure = counts["tenure"]
    rows = [
        (1, "Jumlah total pegawai selama 2025", total_workforce, "Estimasi rekonsiliasi", "848 ASN + 38 outsourcing", "Outsourcing dihitung agregat; identitas per orang tidak ditandai dalam DUK."),
        (2, "Jumlah pegawai yang berstatus ASN selama 2025", total_asn, "Terverifikasi silang", "259 PNS/CPNS + 589 PPPK", "Status pada posisi 31-12-2025."),
        (3, "Jumlah tenaga pemeriksa pajak selama 2025", q("Pemeriksa Pajak"), "Minimum teridentifikasi", "Jabatan/riwayat/diklat eksplisit pemeriksaan pajak", "Bukan penetapan formasi resmi; lihat sheet Bukti Kualifikasi."),
        (4, "Jumlah tenaga juru sita selama 2025", q("Juru Sita Pajak"), "Minimum teridentifikasi", "Jabatan/diklat eksplisit jurusita pajak", "Lihat sheet Bukti Kualifikasi."),
        (5, "Jumlah tenaga penagihan pajak selama 2025", q("Penagihan Pajak"), "Minimum teridentifikasi", "Riwayat jabatan relevan di Bapenda sejak 2020", "Jabatan terakhir JSON banyak digeneralisasi; angka memakai fungsi spesifik terakhir yang tersedia."),
        (6, "Jumlah tenaga pendata pajak selama 2025", q("Pendata Pajak"), "Minimum teridentifikasi", "Riwayat jabatan relevan di Bapenda sejak 2020", "Lihat sheet Bukti Kualifikasi."),
        (7, "Jumlah tenaga penilai PBB-P2 selama 2025", q("Penilai PBB-P2") or None, "Tidak cukup data" if not q("Penilai PBB-P2") else "Minimum teridentifikasi", "Hanya bukti yang menyebut penilai dan PBB/Pajak Bumi", "Dikosongkan karena tidak ada bukti eksplisit pada sumber; ini bukan kepastian tidak ada petugas."),
        (8, "Jumlah tenaga di bidang IT/sistem perpajakan daerah selama 2025", q("IT/Sistem Perpajakan"), "Minimum teridentifikasi", "Riwayat/diklat SIPDA + jabatan kontrak Tenaga Operator Komputer", "Lihat sheet Bukti Kualifikasi."),
        (9, "Jumlah pegawai dengan sertifikasi keahlian tertentu (penyidikan) selama 2025", q("Penyidikan"), "Minimum teridentifikasi", "Diklat/jabatan penyidik yang eksplisit", "Lihat sheet Bukti Kualifikasi."),
        (10, "Jumlah Tenaga Administrasi Kepegawaian selama 2025", q("Administrasi Kepegawaian"), "Minimum teridentifikasi", "Jabatan/diklat Analis Kepegawaian/SDM Aparatur", "Lihat sheet Bukti Kualifikasi."),
        (11, "Jumlah pegawai lulusan S2 selama 2025", education["S2"], "ASN saja", "Pendidikan tertinggi 848 ASN", f"S3 terpisah dan tidak dijumlahkan ke S2: {education['S3']} orang."),
        (12, "Jumlah pegawai lulusan D4/S1 selama 2025", education["D4/S1"], "ASN saja", "Pendidikan tertinggi 848 ASN", "Outsourcing tidak dapat dipisahkan per individu dari daftar PHL+OS."),
        (13, "Jumlah pegawai lulusan D3 selama 2025", education["D3"], "ASN saja", "Pendidikan tertinggi 848 ASN", ""),
        (14, "Jumlah pegawai lulusan D1 selama 2025", education["D1"], "ASN saja", "Pendidikan tertinggi 848 ASN", ""),
        (15, "Jumlah pegawai lulusan SMA selama 2025", education["SMA/sederajat"], "ASN saja", "Pendidikan tertinggi 848 ASN", "Mencakup SMA/SMK/MA/SLTA/Paket C."),
        (16, "Jumlah total anggaran pegawai selama 2025", None, "Data tidak tersedia", "Tidak ada field anggaran dalam DUK/JSON", "Dikosongkan sesuai instruksi pengguna."),
        (17, "Jumlah anggaran pengembangan pegawai selama 2025", None, "Data tidak tersedia", "Tidak ada nilai rupiah pada riwayat diklat", "Dikosongkan sesuai instruksi pengguna."),
        (18, "Penghasilan (take home pay) pegawai tertinggi selama 2025", None, "Data tidak tersedia", "Tidak ada data penghasilan/payroll", "Dikosongkan sesuai instruksi pengguna."),
        (19, "Penghasilan (take home pay) pegawai terendah selama 2025", None, "Data tidak tersedia", "Tidak ada data penghasilan/payroll", "Dikosongkan sesuai instruksi pengguna."),
        (20, "Jumlah pegawai usia sampai dengan 30 tahun selama 2025", age["<=30"], "ASN saja", "Usia tepat pada 31-12-2025; N=848 ASN", "Tanggal lahir diambil dari JSON, fallback dari NIP."),
        (21, "Jumlah pegawai usia antara 31-45 tahun selama 2025", age["31-45"], "ASN saja", "Usia tepat pada 31-12-2025; N=848 ASN", ""),
        (22, "Jumlah pegawai usia di atas 45 tahun selama 2025", age[">45"], "ASN saja", "Usia tepat pada 31-12-2025; N=848 ASN", ""),
        (23, "Jumlah pegawai masa kerja antara 0-10 tahun selama 2025", tenure["0-10"], "ASN saja", "Masa kerja ASN s.d. 31-12-2025; N=848", "PPPK memakai tahun pengangkatan 2025 dari NIP PPPK."),
        (24, "Jumlah pegawai masa kerja antara 11-20 tahun selama 2025", tenure["11-20"], "ASN saja", "Masa kerja ASN s.d. 31-12-2025; N=848", ""),
        (25, "Jumlah pegawai masa kerja antara 21-30 tahun selama 2025", tenure["21-30"], "ASN saja", "Masa kerja ASN s.d. 31-12-2025; N=848", ""),
        (26, "Jumlah pegawai masa kerja lebih dari 30 tahun selama 2025", tenure[">30"], "ASN saja", "Masa kerja ASN s.d. 31-12-2025; N=848", ""),
        (27, "Jumlah laporan whistle blower/pelapor selama 2025", None, "Data tidak tersedia", "Tidak ada pada DUK/JSON kepegawaian", "Parameter KI & Transparansi pada foto; dikosongkan."),
        (28, "Jumlah laporan whistle blower ditindaklanjuti selama 2025", None, "Data tidak tersedia", "Tidak ada pada DUK/JSON kepegawaian", "Parameter KI & Transparansi pada foto; dikosongkan."),
        (29, "Jumlah temuan dalam laporan audit selama 2025", None, "Data tidak tersedia", "Tidak ada pada DUK/JSON kepegawaian", "Parameter KI & Transparansi pada foto; dikosongkan."),
        (30, "Nilai rupiah temuan dalam laporan audit selama 2025", None, "Data tidak tersedia", "Tidak ada pada DUK/JSON kepegawaian", "Parameter KI & Transparansi pada foto; dikosongkan."),
        (31, "Jumlah temuan dalam laporan audit ditindaklanjuti selama 2025", None, "Data tidak tersedia", "Tidak ada pada DUK/JSON kepegawaian", "Parameter KI & Transparansi pada foto; dikosongkan."),
        (32, "Jumlah temuan pelanggaran SOP selama 2025", None, "Data tidak tersedia", "Tidak ada pada DUK/JSON kepegawaian", "Parameter KI & Transparansi pada foto; dikosongkan."),
        (33, "Jumlah temuan pelanggaran SOP ditindaklanjuti selama 2025", None, "Data tidak tersedia", "Tidak ada pada DUK/JSON kepegawaian", "Parameter KI & Transparansi pada foto; dikosongkan."),
    ]
    start_row = 5
    status_fills = {
        "Terverifikasi silang": "C6E0B4",
        "Estimasi rekonsiliasi": "FFE699",
        "Minimum teridentifikasi": "FCE4D6",
        "ASN saja": "DDEBF7",
        "Data tidak tersedia": "D9E1F2",
        "Tidak cukup data": "E7E6E6",
    }
    for row_idx, row in enumerate(rows, start_row):
        for col, value in enumerate(row, 1):
            cell = ws.cell(row_idx, col, value)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(bottom=Side(style="hair", color="D9E2F3"))
        status_cell = ws.cell(row_idx, 4)
        status_cell.fill = PatternFill("solid", fgColor=status_fills.get(text(status_cell.value), "FFFFFF"))
        ws.cell(row_idx, 3).alignment = Alignment(horizontal="center", vertical="top")
    add_table(ws, 4, 4 + len(rows), 6, "TabelRekapSDM2025")
    apply_sheet_style(ws, {"A": 7, "B": 54, "C": 14, "D": 24, "E": 48, "F": 58}, "A5")
    ws.auto_filter.ref = f"A4:F{4 + len(rows)}"

    # Ringkasan rekonsiliasi.
    wr = wb.create_sheet("REKONSILIASI")
    make_title(
        wr,
        "REKONSILIASI SNAPSHOT PEGAWAI",
        "Alur koreksi yang menghasilkan posisi 31 Desember 2025. Tanggal efektif lebih kuat daripada keberadaan nama pada salah satu snapshot.",
        6,
    )
    recon_headers = ["Urutan", "Komponen", "Jumlah", "Perlakuan", "Hasil/Implikasi", "Sumber"]
    for c, h in enumerate(recon_headers, 1):
        cell = wr.cell(4, c, h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4472C4")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    recon_rows = [
        (1, "DUK utama Oktober 2025", len(excel["main_by_nip"]), "Titik awal", "260 PNS/CPNS + 46 PPPK", "Sheet DUK PNS SESUAI UNIT KERJA OKTOB"),
        (2, "Pensiun efektif 01-11-2025", 1, "Dikeluarkan", "Tidak aktif pada 31-12-2025", f"NIP {RETIRED_2025_NIP}"),
        (3, "BUP efektif 01-01-2026", 1, "Tetap dimasukkan", "Masih aktif tepat 31-12-2025; ditambah kembali bila basisnya JSON", f"NIP {RETAIN_FROM_EXCEL_NIP}"),
        (4, "Mutasi masuk efektif setelah cut-off", 3, "Dikeluarkan dari JSON", "Efektif 01-01-2026 / 01-02-2026", "Lihat tiga NIP pada catatan metode"),
        (5, "PPPK pada DUK Oktober", len(excel["pppk_nips"]), "Tetap ASN", "Bagian dari 589 PPPK akhir 2025", "Sheet DUK PPPK BAPENDA"),
        (6, "PHL yang berubah menjadi PPPK", excel["phl_count"], "Status diperbarui", "589 PPPK = 46 PPPK awal + 543 PHL", "Rekap PHL + JSON"),
        (7, "Outsourcing", outsourcing, "Tetap non-ASN (agregat)", "Menambah total tenaga kerja, tidak menambah ASN", "Copy of REKAPITULASI PHL — kolom Outsourcing"),
        (8, "Posisi akhir ASN", total_asn, "Hasil", "259 PNS/CPNS + 589 PPPK", "Daftar ASN 31-12-2025"),
        (9, "Posisi akhir total tenaga kerja", total_workforce, "Hasil", "848 ASN + 38 outsourcing", "Hasil rekonsiliasi"),
    ]
    for rr, row in enumerate(recon_rows, 5):
        for cc, value in enumerate(row, 1):
            wr.cell(rr, cc, value).alignment = Alignment(vertical="top", wrap_text=True)
    add_table(wr, 4, 4 + len(recon_rows), 6, "TabelRekonsiliasi")
    apply_sheet_style(wr, {"A": 9, "B": 38, "C": 12, "D": 25, "E": 45, "F": 45}, "A5")

    # Daftar ASN hasil rekonsiliasi.
    wa = wb.create_sheet("DAFTAR ASN 31-12-2025")
    make_title(
        wa,
        "DAFTAR ASN BAPENDA — 31 DESEMBER 2025",
        "Berisi 848 ASN setelah mengeluarkan tiga mutasi 2026 dan menambahkan kembali pegawai dengan BUP 1 Januari 2026.",
        15,
    )
    asn_headers = [
        "No.", "NIP", "NIK", "Nama", "Status", "Kedudukan", "Jabatan Terakhir", "Unit Kerja",
        "Tanggal Lahir", "Usia", "Pendidikan Tertinggi", "Detail Pendidikan", "TMT Awal ASN",
        "Masa Kerja (tahun)", "Sumber/Perlakuan",
    ]
    for c, h in enumerate(asn_headers, 1):
        cell = wa.cell(4, c, h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4472C4")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for i, person in enumerate(roster, 1):
        values = [
            i,
            text(person.get("nip")),
            digits(person.get("nik")),
            text(person.get("namaWithGelar") or person.get("nama")),
            text(person.get("statusKepegawaian")),
            text(person.get("kedudukanKepegawaian")),
            text(person.get("jabatanTerakhir")),
            text(person.get("skpd")),
            person.get("_dob"),
            person.get("_age"),
            text(person.get("_edu_label")),
            text(person.get("_edu_detail")),
            person.get("_start"),
            person.get("_tenure"),
            text(person.get("_source")),
        ]
        row_no = 4 + i
        for c, value in enumerate(values, 1):
            cell = wa.cell(row_no, c, value)
            cell.alignment = Alignment(vertical="top", wrap_text=c in {4, 6, 7, 8, 12, 15})
        wa.cell(row_no, 2).number_format = "@"
        wa.cell(row_no, 3).number_format = "@"
        wa.cell(row_no, 9).number_format = "dd-mm-yyyy"
        wa.cell(row_no, 13).number_format = "dd-mm-yyyy"
    add_table(wa, 4, 4 + len(roster), len(asn_headers), "TabelASN31122025")
    apply_sheet_style(
        wa,
        {"A": 7, "B": 21, "C": 19, "D": 34, "E": 10, "F": 24, "G": 40, "H": 48,
         "I": 14, "J": 8, "K": 20, "L": 32, "M": 14, "N": 18, "O": 46},
        "A5",
    )

    # Bukti kualifikasi.
    wk = wb.create_sheet("BUKTI KUALIFIKASI")
    make_title(
        wk,
        "BUKTI KUALIFIKASI/FUNGSI KHUSUS",
        "Satu orang dapat memiliki lebih dari satu bukti dan masuk lebih dari satu kategori. Angka rekap menghitung orang unik per kategori.",
        8,
    )
    k_headers = ["No.", "Kategori", "NIP", "NIK", "Nama", "Jenis Bukti", "Bukti", "Tanggal/Tahun"]
    for c, h in enumerate(k_headers, 1):
        cell = wk.cell(4, c, h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4472C4")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    qualification_evidence.sort(key=lambda x: (x["kategori"], x["nama"], x["jenis_bukti"], x["bukti"]))
    for i, ev in enumerate(qualification_evidence, 1):
        vals = [i, ev["kategori"], ev["nip"], ev["nik"], ev["nama"], ev["jenis_bukti"], ev["bukti"], ev["tanggal_tahun"]]
        for c, value in enumerate(vals, 1):
            cell = wk.cell(4 + i, c, value)
            cell.alignment = Alignment(vertical="top", wrap_text=c in {5, 6, 7})
        wk.cell(4 + i, 3).number_format = "@"
        wk.cell(4 + i, 4).number_format = "@"
    add_table(wk, 4, 4 + len(qualification_evidence), len(k_headers), "TabelBuktiKualifikasi")
    apply_sheet_style(wk, {"A": 7, "B": 25, "C": 21, "D": 19, "E": 34, "F": 24, "G": 72, "H": 15}, "A5")

    # Daftar sumber PHL + outsourcing, agar 38 outsourcing bisa ditelusuri
    # lagi bila pengguna memperoleh penanda vendor/per individu.
    wp = wb.create_sheet("SUMBER PHL+OS 2025")
    make_title(
        wp,
        "DAFTAR SUMBER PHL + OUTSOURCING 2025",
        "Salinan terpilih dari DUK 2025 (581 orang). Workbook sumber hanya memberi jumlah outsourcing per unit, bukan penanda outsourcing pada setiap baris.",
        14,
    )
    p_headers = [
        "No.", "Baris Sumber", "Nama", "NIK", "Tempat Lahir", "Tanggal Lahir", "Jenis Kelamin",
        "Pendidikan", "Program Studi", "TMT Pertama", "Unit", "Jenis Jabatan", "Jabatan Kontrak", "Status Seleksi",
    ]
    for c, h in enumerate(p_headers, 1):
        cell = wp.cell(4, c, h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4472C4")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    for i, person in enumerate(excel["phl_records"], 1):
        vals = [
            i, person["row"], person["nama"], person["nik"], person["tempat_lahir"], person["tanggal_lahir"],
            person["jenis_kelamin"], person["pendidikan"], person["program_studi"], person["tmt_pertama"],
            person["unit"], person["jenis_jabatan"], person["jabatan_kontrak"], person["status_seleksi"],
        ]
        for c, value in enumerate(vals, 1):
            cell = wp.cell(4 + i, c, value)
            cell.alignment = Alignment(vertical="top", wrap_text=c in {3, 9, 11, 13, 14})
        wp.cell(4 + i, 4).number_format = "@"
        if isinstance(person["tanggal_lahir"], (date, datetime)):
            wp.cell(4 + i, 6).number_format = "dd-mm-yyyy"
        if isinstance(person["tmt_pertama"], (date, datetime)):
            wp.cell(4 + i, 10).number_format = "dd-mm-yyyy"
    add_table(wp, 4, 4 + len(excel["phl_records"]), len(p_headers), "TabelSumberPHLOS")
    apply_sheet_style(
        wp,
        {"A": 7, "B": 12, "C": 32, "D": 19, "E": 20, "F": 14, "G": 14, "H": 17,
         "I": 28, "J": 14, "K": 44, "L": 18, "M": 32, "N": 24},
        "A5",
    )

    # Catatan metode dan definisi.
    wm = wb.create_sheet("CATATAN METODE")
    make_title(
        wm,
        "CATATAN METODE, ASUMSI, DAN BATASAN",
        "Baca sheet ini sebelum memakai angka untuk laporan resmi. Semua asumsi material dicatat di sini.",
        3,
    )
    method_rows = [
        ("Tanggal potong", "31 Desember 2025", "Semua umur, masa kerja, status, pensiun, dan mutasi dinilai terhadap tanggal ini."),
        ("Snapshot Excel", "Sekitar Oktober 2025", "Disimpulkan dari nama sheet utama: DUK PNS SESUAI UNIT KERJA OKTOB."),
        ("Snapshot JSON", "Sesudah awal 2026", "Walau diperkirakan Januari, JSON memuat mutasi efektif 1 Februari 2026; karena itu tanggal efektif dipakai untuk menyaring."),
        ("Mutasi 2026 dikeluarkan", ", ".join(POST_CUTOFF_NIPS), "; ".join(POST_CUTOFF_NIPS.values())),
        ("BUP 1 Januari 2026 dipertahankan", RETAIN_FROM_EXCEL_NIP, "Aktif sampai 31 Desember 2025, sehingga harus ditambah ke roster JSON."),
        ("Pensiun November dikeluarkan", RETIRED_2025_NIP, "BUP 1 November 2025; tidak aktif pada tanggal potong."),
        ("Total pegawai", "886", "848 ASN + 38 outsourcing. Outsourcing tersedia hanya sebagai angka agregat."),
        ("Status ASN", "848", "259 PNS/CPNS dan 589 PPPK."),
        ("PPPK", "589", "46 sudah muncul pada DUK Oktober + 543 yang merupakan perubahan status dari PHL; kesamaan angka diverifikasi antar-sheet."),
        ("Pendidikan", "ASN saja", "Pendidikan tertinggi diambil dari riwayat JSON; fallback dari Excel berdasarkan NIP/NIK. S3 tidak digabung ke S2."),
        ("Umur", "ASN saja", "Tanggal lahir JSON; fallback delapan digit awal NIP. Batas: <=30, 31-45, >45."),
        ("Masa kerja", "ASN saja", "PNS/CPNS: TMT pangkat paling awal atau segmen NIP. PPPK: tahun pengangkatan 2025 pada NIP. Batas kategori inklusif."),
        ("Fungsi/keahlian khusus", "Minimum teridentifikasi", "Jabatan terakhir JSON sudah banyak digeneralisasi; angka memakai bukti eksplisit pada riwayat jabatan, diklat, atau jabatan kontrak 2025."),
        ("Penilai PBB-P2", "0 bukti eksplisit", "Tidak ditafsirkan sebagai kepastian tidak ada petugas; sumber tidak menyebut peran/sertifikasi ini secara eksplisit."),
        ("Anggaran dan THP", "Tidak tersedia", "Tidak ada data rupiah atau payroll dalam kedua sumber; sengaja dikosongkan."),
        ("KI & Transparansi", "Tidak tersedia", "Foto meminta data whistle blower, audit, dan SOP; kedua sumber adalah data kepegawaian dan tidak memuat parameter tersebut."),
        ("Privasi", "Data lokal", "Workbook memuat NIP/NIK karena dibutuhkan untuk rekonsiliasi. Simpan dan bagikan secara terbatas."),
    ]
    m_headers = ["Topik", "Keputusan/Nilai", "Penjelasan"]
    for c, h in enumerate(m_headers, 1):
        cell = wm.cell(4, c, h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4472C4")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    for rr, row in enumerate(method_rows, 5):
        for cc, value in enumerate(row, 1):
            wm.cell(rr, cc, value).alignment = Alignment(vertical="top", wrap_text=True)
    add_table(wm, 4, 4 + len(method_rows), 3, "TabelCatatanMetode")
    apply_sheet_style(wm, {"A": 34, "B": 42, "C": 88}, "A5")

    # Format umum dan properti dokumen.
    thin = Side(style="thin", color="D9E2F3")
    for sheet in wb.worksheets:
        for row in sheet.iter_rows(min_row=4):
            for cell in row:
                if cell.value is not None:
                    cell.border = Border(bottom=thin)
        sheet.page_setup.orientation = "landscape"
        sheet.page_setup.fitToWidth = 1
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.oddFooter.center.text = "Bapenda Kota Medan — Rekap per 31 Desember 2025"
        sheet.oddFooter.right.text = "Halaman &P dari &N"

    wb.properties.title = "Rekap Pegawai Bapenda per 31 Desember 2025"
    wb.properties.subject = "Rekonsiliasi DUK Oktober 2025 dan snapshot JSON pasca-2025"
    wb.properties.creator = "Codex"
    wb.save(OUTPUT)


def main() -> None:
    if not EXCEL_SOURCE.exists():
        raise FileNotFoundError(EXCEL_SOURCE)
    if not JSON_SOURCE.exists():
        raise FileNotFoundError(JSON_SOURCE)

    excel = extract_excel_sources(EXCEL_SOURCE)
    with JSON_SOURCE.open(encoding="utf-8") as fh:
        json_rows = json.load(fh)

    assert len(json_rows) == 850
    assert len(excel["main_by_nip"]) == 306
    assert len(excel["pppk_nips"]) == 46
    assert len(excel["phl_records"]) == 581
    assert excel["phl_count"] == 543
    assert excel["outsourcing_count"] == 38
    assert excel["total_phl_os"] == 581

    roster = enrich_roster(build_roster(json_rows, excel), excel)
    qualifications, evidence = collect_qualification_evidence(roster, excel["phl_records"])
    write_workbook(roster, excel, qualifications, evidence)

    counts = group_counts(roster)
    summary = {
        "output": str(OUTPUT),
        "asn": len(roster),
        "status": dict(counts["status"]),
        "total_dengan_outsourcing": len(roster) + excel["outsourcing_count"],
        "pendidikan": dict(counts["education"]),
        "usia": dict(counts["age"]),
        "masa_kerja": dict(counts["tenure"]),
        "kualifikasi_minimum": {k: len(v) for k, v in sorted(qualifications.items())},
        "bukti_kualifikasi": len(evidence),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
