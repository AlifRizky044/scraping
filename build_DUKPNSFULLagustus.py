#!/usr/bin/env python3
"""Build a full August employee JSON using April data plus August HTML sources."""

from __future__ import annotations

import copy
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from generate_laporan_perbandingan_pns import normalize_for_comparison, parse_august_data


BASE_DIR = Path(__file__).resolve().parent
APRIL_PATH = BASE_DIR / "DUKPNSFULLapril.json"
AUGUST_LIST_PATH = BASE_DIR / "datamentah.txt"
AUGUST_DETAIL_PATH = BASE_DIR / "datamentahdetail.txt"
OUTPUT_PATH = BASE_DIR / "DUKPNSFULLagustus.json"
REPORT_PATH = BASE_DIR / "laporan_pembaruan_DUKPNSFULLagustus.md"
SIMPEG_BASE_URL = "https://bkpsdm.medan.go.id/simpeg/"

SUMMARY_FIELDS = (
    "namaWithGelar",
    "kedudukan",
    "tempatTglLahir",
    "golonganTerakhir",
    "jabatanTerakhir",
    "skpd",
)

PROFILE_INPUT_MAP = {
    "nip": "nip",
    "nipLama": "nip_lama",
    "tempatLahir": "tempat_lahir",
    "tanggalLahir": "tanggal_lahir",
    "alamat": "alamat",
    "provinsi": "id_provinsi",
    "kota": "id_kabupaten",
    "kecamatan": "id_kecamatan",
    "kelurahan": "id_kelurahan",
    "rt": "rt",
    "rw": "rw",
    "kodePos": "kode_pos",
    "noTel": "no_telp",
    "noHp": "no_hp",
    "email": "email",
    "tinggi": "tinggi",
    "berat": "berat",
    "suku": "id_suku",
    "marga": "marga",
    "cacat": "cacat_tubuh",
    "ciriKhas": "ciri_khas",
    "hobi": "hobi",
    "nik": "ktp",
    "taspen": "taspen",
    "karpeg": "no_karpeg",
    "askes": "no_askes",
    "npwp": "npwp",
    "gelarDepan": "gelar_depan",
    "nama": "nama_pegawai",
    "gelarBelakang": "gelar_belakang",
}

PROFILE_SELECT_MAP = {
    "kedudukanKepegawaian": "id_kedudukan_kepegawaian",
    "jenisKepegawaian": "id_jenis_kepegawaian",
    "statusKepegawaian": "id_status_kepegawaian",
    "agama": "id_agama",
    "statusPernikahan": "id_status_pernikahan",
    "jenisKelamin": "id_jenis_kelamin",
    "golDarah": "id_golongan_darah",
    "rambut": "id_rambut",
    "bentukMuka": "id_bentuk_muka",
    "warnaKulit": "id_warna_kulit",
}


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def absolute_url(href: str) -> str:
    return urljoin(SIMPEG_BASE_URL, href) if href else ""


class ProfileParser(HTMLParser):
    """Extract input values, selected options, and supporting-document links."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.inputs: dict[str, str] = {}
        self.selected: dict[str, str] = {}
        self.links: list[str] = []
        self.current_select = ""
        self.current_option_selected = False
        self.current_option_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "input":
            name = attributes.get("name")
            if name and name not in self.inputs:
                self.inputs[name] = attributes.get("value") or ""
        elif tag == "select":
            self.current_select = attributes.get("id") or attributes.get("name") or ""
        elif tag == "option" and self.current_select:
            self.current_option_selected = "selected" in attributes
            self.current_option_parts = []
        elif tag == "a":
            classes = (attributes.get("class") or "").split()
            href = attributes.get("href") or ""
            if "link_auto_panel" in classes and href:
                self.links.append(href)

    def handle_data(self, data: str) -> None:
        if self.current_select and self.current_option_selected:
            self.current_option_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "option" and self.current_select:
            if self.current_option_selected:
                self.selected[self.current_select] = clean("".join(self.current_option_parts))
            self.current_option_selected = False
            self.current_option_parts = []
        elif tag == "select":
            self.current_select = ""


@dataclass
class TableCell:
    text: str = ""
    verified: bool = False
    hrefs: list[str] = field(default_factory=list)
    classes: set[str] = field(default_factory=set)


class HistoryTableParser(HTMLParser):
    """Extract body rows from the first DataTables_Table_0 in a page fragment."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_table = False
        self.table_depth = 0
        self.found_table = False
        self.in_tbody = False
        self.in_row = False
        self.in_cell = False
        self.rows: list[list[TableCell]] = []
        self.current_row: list[TableCell] = []
        self.current_parts: list[str] = []
        self.current_verified = False
        self.current_hrefs: list[str] = []
        self.current_classes: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "table" and not self.found_table and attributes.get("id") == "DataTables_Table_0":
            self.in_table = True
            self.found_table = True
            self.table_depth = 1
            return
        if self.in_table and tag == "table":
            self.table_depth += 1
        if not self.in_table:
            return
        if tag == "tbody":
            self.in_tbody = True
        elif self.in_tbody and tag == "tr":
            self.in_row = True
            self.current_row = []
        elif self.in_row and tag == "td":
            self.in_cell = True
            self.current_parts = []
            self.current_verified = False
            self.current_hrefs = []
            self.current_classes = set((attributes.get("class") or "").split())
        elif self.in_cell:
            classes = set((attributes.get("class") or "").split())
            if "btn-success" in classes:
                self.current_verified = True
            if tag == "a" and attributes.get("href"):
                self.current_hrefs.append(attributes["href"] or "")

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.current_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.in_table:
            return
        if tag == "td" and self.in_cell:
            self.current_row.append(
                TableCell(
                    text=clean("".join(self.current_parts)),
                    verified=self.current_verified,
                    hrefs=self.current_hrefs,
                    classes=self.current_classes,
                )
            )
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            self.rows.append(self.current_row)
            self.in_row = False
        elif tag == "tbody":
            self.in_tbody = False
        elif tag == "table":
            self.table_depth -= 1
            if self.table_depth == 0:
                self.in_table = False


def extract_history_rows(segment: str) -> tuple[bool, list[list[TableCell]]]:
    parser = HistoryTableParser()
    parser.feed(segment)
    rows = parser.rows
    if rows and any("dataTables_empty" in cell.classes for cell in rows[0]):
        rows = []
    return parser.found_table, rows


def choose_file(row: list[TableCell], indexes: tuple[int, ...]) -> str:
    for index in indexes:
        if index < len(row) and row[index].hrefs:
            return absolute_url(row[index].hrefs[0])
    return ""


def parse_education(segment: str) -> tuple[bool, list[dict[str, str]]]:
    found, rows = extract_history_rows(segment)
    result: list[dict[str, str]] = []
    for row_number, row in enumerate(rows, start=1):
        if len(row) < 13:
            raise ValueError(f"Riwayat pendidikan baris {row_number} hanya memiliki {len(row)} kolom")
        result.append(
            {
                "statusVerifikasi": "Terverifikasi" if row[1].verified else "Belum Terverifikasi",
                "tingkatPendidikan": row[2].text,
                "detailPendidikan": row[3].text,
                "namaSekolah": row[4].text,
                "tempat": row[5].text,
                "jurusan": row[6].text,
                "namaKepala": row[7].text,
                "nomorIjazah": row[8].text,
                "tanggalIjazah": row[9].text,
                "ipk": row[10].text,
                "file": choose_file(row, (11, 12)),
            }
        )
    return found, result


def parse_ranks(segment: str) -> tuple[bool, list[dict[str, str]]]:
    found, rows = extract_history_rows(segment)
    result: list[dict[str, str]] = []
    for row_number, row in enumerate(rows, start=1):
        if len(row) < 14:
            raise ValueError(f"Riwayat pangkat baris {row_number} hanya memiliki {len(row)} kolom")
        result.append(
            {
                "no": row[2].text,
                "statusVerifikasi": "Terverifikasi" if row[1].verified else "Belum Terverifikasi",
                "pangkat": row[3].text,
                "tmt": row[4].text,
                "noSk": row[5].text,
                "tglSk": row[6].text,
                "pejabatPenandatangan": row[7].text,
                "mkgTahun": row[8].text,
                "mkgBulan": row[9].text,
                "file": choose_file(row, (10, 11)),
                "catatan": row[13].text,
            }
        )
    return found, result


def parse_jobs(segment: str) -> tuple[bool, list[dict[str, str]]]:
    found, rows = extract_history_rows(segment)
    result: list[dict[str, str]] = []
    for row_number, row in enumerate(rows, start=1):
        if len(row) < 16:
            raise ValueError(f"Riwayat jabatan baris {row_number} hanya memiliki {len(row)} kolom")
        result.append(
            {
                "no": row[1].text,
                "statusVerifikasi": "Terverifikasi" if row[2].verified else "Belum Terverifikasi",
                "tipeJabatan": row[3].text,
                "tmt": row[8].text,
                "jabatan": row[4].text,
                "jenjang": row[5].text,
                "eselon": row[6].text,
                "skpd": row[7].text,
                "tmtSk": row[9].text,
                "pejabatPenetapan": row[10].text,
                "keteranganJabatan": row[11].text,
                "file": choose_file(row, (12, 13)),
                "catatan": row[15].text,
            }
        )
    return found, result


def parse_supporting_links(hrefs: list[str]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for href in hrefs:
        params = parse_qs(urlparse(href).query)
        link_type = params.get("type", [""])[0]
        if not link_type:
            continue
        item = (absolute_url(href), link_type)
        if item in seen:
            continue
        seen.add(item)
        links.append({"href": item[0], "type": item[1]})
    return links


def split_detail_chunks(text: str) -> list[tuple[str, str]]:
    # The main profile page uses this exact declaration. History pages use a
    # spaced variant, so they deliberately remain inside the same employee chunk.
    matches = list(re.finditer(r'(?m)^var id_pegawai="(\d+)";\s*$', text))
    chunks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        chunks.append((match.group(1), text[match.start():end]))
    return chunks


def parse_new_employee_details(path: Path, schema_keys: list[str]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    chunks = split_detail_chunks(text)
    parsed: dict[str, dict[str, Any]] = {}
    diagnostics: dict[str, Any] = {
        "detail_chunk_count": len(chunks),
        "missing_history_pages": [],
        "blank_profile_fields": {},
    }

    for employee_id, chunk in chunks:
        education_pos = chunk.find("DATA RIWAYAT PENDIDIKAN")
        rank_pos = chunk.find("DATA RIWAYAT KEPANGKATAN")
        job_pos = chunk.find("DATA RIWAYAT JABATAN")
        positions = (education_pos, rank_pos, job_pos)
        if any(position < 0 for position in positions) or not (education_pos < rank_pos < job_pos):
            raise ValueError(f"Urutan halaman detail tidak lengkap untuk ID pegawai {employee_id}")

        profile_segment = chunk[:education_pos]
        education_segment = chunk[education_pos:rank_pos]
        rank_segment = chunk[rank_pos:job_pos]
        job_segment = chunk[job_pos:]

        profile_parser = ProfileParser()
        profile_parser.feed(profile_segment)
        education_found, education = parse_education(education_segment)
        rank_found, ranks = parse_ranks(rank_segment)
        job_found, jobs = parse_jobs(job_segment)

        nip = digits(profile_parser.inputs.get("nip"))
        if not nip:
            raise ValueError(f"NIP kosong pada detail ID pegawai {employee_id}")

        employee: dict[str, Any] = {key: "" for key in schema_keys}
        for output_key, input_name in PROFILE_INPUT_MAP.items():
            employee[output_key] = clean(profile_parser.inputs.get(input_name))
        for output_key, select_id in PROFILE_SELECT_MAP.items():
            employee[output_key] = clean(profile_parser.selected.get(select_id))
        employee["nip"] = nip
        employee["riwayatDiklatLainnya"] = ""
        employee["riwayatDiklatStruktural"] = ""
        employee["riwayatJabatan"] = jobs if jobs else ""
        employee["riwayatPendidikan"] = education if education else ""
        employee["riwayatPangkat"] = ranks if ranks else ""
        employee["links"] = parse_supporting_links(profile_parser.links)

        missing_pages: list[str] = []
        if not education_found:
            missing_pages.append("riwayatPendidikan")
        if not rank_found:
            missing_pages.append("riwayatPangkat")
        if not job_found:
            missing_pages.append("riwayatJabatan")
        if missing_pages:
            diagnostics["missing_history_pages"].append({"nip": nip, "fields": missing_pages})

        blank_fields = [
            key
            for key in list(PROFILE_INPUT_MAP) + list(PROFILE_SELECT_MAP)
            if key not in {"nip"} and employee.get(key, "") == ""
        ]
        diagnostics["blank_profile_fields"][nip] = blank_fields
        parsed[nip] = employee

    if len(parsed) != len(chunks):
        raise ValueError("NIP duplikat ditemukan pada datamentahdetail.txt")
    return parsed, diagnostics


def derive_titles(employee: dict[str, Any], current_full_name: str) -> tuple[bool, str, str]:
    """Safely split titles around the unchanged base name."""
    base_name = clean(employee.get("nama"))
    if not base_name:
        return False, clean(employee.get("gelarDepan")), clean(employee.get("gelarBelakang"))

    tokens = re.split(r"\s+", base_name)
    base_pattern = r"\s+".join(re.escape(token) for token in tokens)
    match = re.search(base_pattern, current_full_name, flags=re.IGNORECASE)
    if not match:
        return False, clean(employee.get("gelarDepan")), clean(employee.get("gelarBelakang"))

    prefix = current_full_name[: match.start()].strip(" ,")
    suffix = current_full_name[match.end() :].strip(" ,")
    return True, prefix, suffix


def extract_rank_group(rank_text: str) -> str:
    match = re.search(r"\(([IVX]+/[A-E])\)", rank_text.upper())
    return match.group(1) if match else ""


def uppercase_summary(employee: dict[str, Any]) -> None:
    for field_name in SUMMARY_FIELDS:
        employee[field_name] = clean(employee.get(field_name)).upper()


def merge_full_august(
    april_data: list[dict[str, Any]],
    august_list: list[dict[str, Any]],
    new_details: dict[str, dict[str, Any]],
    schema_keys: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    april_by_nip = {digits(employee.get("nip")): employee for employee in april_data}
    august_nips = {digits(employee.get("nip")) for employee in august_list}
    new_nips = august_nips - set(april_by_nip)
    missing_nips = set(april_by_nip) - august_nips

    if new_nips != set(new_details):
        raise ValueError(
            "NIP detail pegawai baru tidak sama dengan selisih daftar Agustus. "
            f"Tanpa detail={sorted(new_nips - set(new_details))}; detail ekstra={sorted(set(new_details) - new_nips)}"
        )

    merged: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "new_nips": sorted(new_nips),
        "missing_nips": sorted(missing_nips),
        "copied_from_april": 0,
        "created_from_august_detail": 0,
        "title_fields_updated": [],
        "title_fields_not_parsed": [],
        "education_details_updated": [],
        "rank_history_mismatches": [],
        "job_history_mismatches": [],
    }

    for summary in august_list:
        nip = digits(summary.get("nip"))
        if nip in april_by_nip:
            employee = copy.deepcopy(april_by_nip[nip])
            report["copied_from_april"] += 1
        else:
            employee = copy.deepcopy(new_details[nip])
            report["created_from_august_detail"] += 1

        old_full_name = clean(employee.get("namaWithGelar"))
        new_full_name = clean(summary.get("namaWithGelar"))
        if nip in april_by_nip and normalize_for_comparison(old_full_name) != normalize_for_comparison(new_full_name):
            parsed, title_prefix, title_suffix = derive_titles(employee, new_full_name)
            if parsed:
                employee["gelarDepan"] = title_prefix
                employee["gelarBelakang"] = title_suffix
                report["title_fields_updated"].append(nip)
            else:
                report["title_fields_not_parsed"].append(nip)

        employee["nip"] = nip
        employee["namaWithGelar"] = new_full_name
        employee["kedudukanKepegawaian"] = clean(summary.get("kedudukanKepegawaian"))
        employee["statusKepegawaian"] = clean(summary.get("statusKepegawaian"))
        employee["kedudukan"] = clean(summary.get("kedudukan"))
        employee["tempatLahir"] = clean(summary.get("tempatLahir"))
        employee["tanggalLahir"] = clean(summary.get("tanggalLahir"))
        employee["tempatTglLahir"] = clean(summary.get("tempatTglLahir")).replace("\n", "\n")
        employee["golonganTerakhir"] = clean(summary.get("golonganTerakhir"))
        employee["jabatanTerakhir"] = clean(summary.get("jabatanTerakhir"))
        employee["skpd"] = clean(summary.get("skpd"))

        if nip in april_by_nip:
            history = employee.get("riwayatPendidikan")
            current_education = clean(summary.get("pendidikanTerakhir"))
            if isinstance(history, list) and history:
                prior_education = clean(history[-1].get("detailPendidikan") or history[-1].get("tingkatPendidikan"))
                if normalize_for_comparison(prior_education) != normalize_for_comparison(current_education):
                    history[-1]["detailPendidikan"] = current_education
                    report["education_details_updated"].append(nip)

        uppercase_summary(employee)
        employee = {key: employee.get(key, "") for key in schema_keys}
        merged.append(employee)

    for employee in merged:
        status = employee.get("statusKepegawaian")
        if status not in {"PNS", "CPNS"}:
            continue

        rank_history = employee.get("riwayatPangkat")
        current_group = clean(employee.get("golonganTerakhir")).upper()
        if current_group:
            latest_group = ""
            if isinstance(rank_history, list) and rank_history:
                latest_group = extract_rank_group(clean(rank_history[-1].get("pangkat")))
            if latest_group != current_group:
                report["rank_history_mismatches"].append(
                    {
                        "nip": employee["nip"],
                        "nama": employee["namaWithGelar"],
                        "golonganTerakhir": current_group,
                        "golonganRiwayatTerakhir": latest_group or "TIDAK TERSEDIA",
                    }
                )

        job_history = employee.get("riwayatJabatan")
        if isinstance(job_history, list) and job_history:
            latest_job = clean(job_history[-1].get("jabatan"))
            latest_skpd = clean(job_history[-1].get("skpd"))
        else:
            latest_job = ""
            latest_skpd = ""
        current_job = clean(employee.get("jabatanTerakhir"))
        current_skpd = clean(employee.get("skpd"))
        job_differs = normalize_for_comparison(latest_job) != normalize_for_comparison(current_job)
        skpd_differs = normalize_for_comparison(latest_skpd) != normalize_for_comparison(current_skpd)
        if job_differs or skpd_differs:
            report["job_history_mismatches"].append(
                {
                    "nip": employee["nip"],
                    "nama": employee["namaWithGelar"],
                    "jabatanAgustus": current_job or "KOSONG",
                    "jabatanRiwayatTerakhir": latest_job or "TIDAK TERSEDIA",
                    "skpdAgustus": current_skpd or "KOSONG",
                    "skpdRiwayatTerakhir": latest_skpd or "TIDAK TERSEDIA",
                    "bidangBerbeda": ", ".join(
                        label for differs, label in ((job_differs, "jabatan"), (skpd_differs, "SKPD")) if differs
                    ),
                }
            )

    return merged, report


def validate_output(data: list[dict[str, Any]], schema_keys: list[str], august_list: list[dict[str, Any]]) -> None:
    if len(data) != len(august_list):
        raise ValueError(f"Jumlah output {len(data)} tidak sama dengan daftar Agustus {len(august_list)}")
    if any(list(employee.keys()) != schema_keys for employee in data):
        raise ValueError("Urutan atau daftar key output tidak sama dengan format April")

    output_nips = [digits(employee.get("nip")) for employee in data]
    source_nips = [digits(employee.get("nip")) for employee in august_list]
    if output_nips != source_nips:
        raise ValueError("Urutan NIP output tidak sama dengan daftar Agustus")
    if len(set(output_nips)) != len(output_nips) or "" in output_nips:
        raise ValueError("NIP output kosong atau duplikat")

    for employee, summary in zip(data, august_list):
        comparisons = {
            "namaWithGelar": summary.get("namaWithGelar"),
            "kedudukan": summary.get("kedudukan"),
            "tempatTglLahir": summary.get("tempatTglLahir"),
            "golonganTerakhir": summary.get("golonganTerakhir"),
            "jabatanTerakhir": summary.get("jabatanTerakhir"),
            "skpd": summary.get("skpd"),
        }
        for field_name, expected in comparisons.items():
            if normalize_for_comparison(employee.get(field_name)) != normalize_for_comparison(expected):
                raise ValueError(f"Field {field_name} tidak sinkron untuk NIP {employee['nip']}")


def render_report(
    full_data: list[dict[str, Any]],
    merge_report: dict[str, Any],
    detail_diagnostics: dict[str, Any],
    april_by_nip: dict[str, dict[str, Any]],
) -> str:
    new_employees = [employee for employee in full_data if employee["nip"] in merge_report["new_nips"]]
    missing_employees = [april_by_nip[nip] for nip in merge_report["missing_nips"]]
    status_counts = Counter(employee.get("statusKepegawaian", "") for employee in full_data)

    lines = [
        "# Laporan Pembaruan DUKPNSFULL Agustus",
        "",
        f"Dibuat: {datetime.now().astimezone().strftime('%d-%m-%Y %H:%M %Z')}",
        "",
        "## Hasil",
        "",
        f"- Total objek Agustus: **{len(full_data)}**.",
        f"- Disalin dari April lalu diperbarui dari daftar Agustus: **{merge_report['copied_from_april']}**.",
        f"- Dibuat dari `datamentahdetail.txt`: **{merge_report['created_from_august_detail']}**.",
        f"- Komposisi status: PNS {status_counts['PNS']}, CPNS {status_counts['CPNS']}, PPPK {status_counts['PPPK']}.",
        "- Semua objek memiliki 52 key dengan nama dan urutan yang sama seperti `DUKPNSFULLapril.json`.",
        "- Urutan output mengikuti nomor urut 1–845 pada daftar Agustus.",
        "",
        "## Pegawai baru yang berhasil dibuat dari detail Agustus",
        "",
    ]
    for employee in new_employees:
        education_count = len(employee["riwayatPendidikan"]) if isinstance(employee["riwayatPendidikan"], list) else 0
        rank_count = len(employee["riwayatPangkat"]) if isinstance(employee["riwayatPangkat"], list) else 0
        job_count = len(employee["riwayatJabatan"]) if isinstance(employee["riwayatJabatan"], list) else 0
        lines.append(
            f"- {employee['nip']} — {employee['namaWithGelar']} "
            f"(pendidikan {education_count}, pangkat {rank_count}, jabatan {job_count})."
        )

    lines.extend(
        [
            "",
            "## Pembaruan yang diterapkan pada pegawai lama",
            "",
            "- Nama/gelar, status/kedudukan, tempat-tanggal lahir, golongan, jabatan, dan SKPD diambil dari daftar Agustus.",
            f"- `gelarDepan`/`gelarBelakang` berhasil diselaraskan untuk **{len(merge_report['title_fields_updated'])}** pegawai yang nama/gelarnya berubah.",
            f"- Detail pendidikan terakhir berhasil diselaraskan untuk **{len(merge_report['education_details_updated'])}** pegawai.",
            "",
            "## Data yang tidak dapat diperbarui atau perlu diperhatikan",
            "",
            "1. `datamentahdetail.txt` hanya berisi detail 7 pegawai baru. Karena itu data pribadi, kontak, dokumen, dan seluruh riwayat 838 pegawai lama tetap berasal dari snapshot April, kecuali field ringkasan serta gelar/pendidikan terakhir yang disebutkan di atas.",
            "2. Halaman riwayat diklat tidak tersedia pada `datamentahdetail.txt`. `riwayatDiklatStruktural` dan `riwayatDiklatLainnya` untuk ketujuh pegawai baru diisi string kosong agar tipenya mengikuti pola file April.",
        ]
    )

    mismatches = merge_report["rank_history_mismatches"]
    if mismatches:
        lines.append(
            f"3. Ada **{len(mismatches)}** pegawai dengan golongan Agustus yang tidak cocok dengan entri terakhir riwayat pangkat yang tersedia. Golongan ringkasan sudah diperbarui, tetapi detail SK/TMT pangkat tidak diubah karena sumbernya tidak tersedia:"
        )
        for item in mismatches:
            lines.append(
                f"   - {item['nip']} — {item['nama']}: {item['golonganRiwayatTerakhir']} → {item['golonganTerakhir']}."
            )
    else:
        lines.append("3. Golongan ringkasan cocok dengan riwayat pangkat terakhir pada seluruh data yang memiliki riwayat.")

    job_mismatches = merge_report["job_history_mismatches"]
    if job_mismatches:
        lines.extend(
            [
                "",
                f"4. Ada **{len(job_mismatches)}** pegawai dengan jabatan dan/atau SKPD Agustus yang berbeda dari entri terakhir `riwayatJabatan`. Field ringkasan sudah diperbarui, tetapi detail SK/TMT riwayat tidak diubah tanpa sumber riwayat terbaru:",
            ]
        )
        for item in job_mismatches:
            lines.append(f"   - {item['nip']} — {item['nama']} (berbeda: {item['bidangBerbeda']})")
            if "jabatan" in item["bidangBerbeda"]:
                lines.append(
                    f"     - Jabatan riwayat: {item['jabatanRiwayatTerakhir']} → ringkasan Agustus: {item['jabatanAgustus']}."
                )
            if "SKPD" in item["bidangBerbeda"]:
                lines.append(
                    f"     - SKPD riwayat: {item['skpdRiwayatTerakhir']} → ringkasan Agustus: {item['skpdAgustus']}."
                )

    blank_profiles = detail_diagnostics["blank_profile_fields"]
    lines.extend(["", "5. Field profil yang memang kosong pada sumber detail pegawai baru:"])
    for employee in new_employees:
        fields = blank_profiles.get(employee["nip"], [])
        field_text = ", ".join(f"`{name}`" for name in fields) if fields else "tidak ada"
        lines.append(f"   - {employee['nip']} — {employee['namaWithGelar']}: {field_text}.")

    if merge_report["title_fields_not_parsed"]:
        lines.extend(
            [
                "",
                "6. Gelar tidak dapat dipecah otomatis pada NIP berikut; namaWithGelar tetap diperbarui, tetapi gelarDepan/gelarBelakang dipertahankan:",
                "   - " + ", ".join(merge_report["title_fields_not_parsed"]),
            ]
        )
    else:
        lines.extend(["", "6. Tidak ada kegagalan pemisahan gelar pada nama yang berubah."])

    if detail_diagnostics["missing_history_pages"]:
        lines.extend(
            [
                "",
                "7. Halaman riwayat yang tidak ditemukan oleh parser:",
                "```json",
                json.dumps(detail_diagnostics["missing_history_pages"], ensure_ascii=False, indent=2),
                "```",
            ]
        )
    else:
        lines.extend(["", "7. Semua halaman pendidikan, pangkat, dan jabatan untuk 7 pegawai baru berhasil dibaca."])

    lines.extend(["", "## Pegawai April yang tidak dimasukkan karena tidak ada di daftar Agustus", ""])
    for employee in missing_employees:
        lines.append(f"- {digits(employee.get('nip'))} — {clean(employee.get('namaWithGelar') or employee.get('nama'))}.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    with APRIL_PATH.open("r", encoding="utf-8") as file:
        april_data = json.load(file)
    if not isinstance(april_data, list) or not april_data:
        raise ValueError("DUKPNSFULLapril.json harus berupa array yang tidak kosong")

    schema_keys = list(april_data[0].keys())
    if len(schema_keys) != 52:
        raise ValueError(f"Format April memiliki {len(schema_keys)} key, diperkirakan 52")
    if any(list(employee.keys()) != schema_keys for employee in april_data):
        raise ValueError("Objek pada format April tidak memiliki urutan key yang konsisten")

    august_list = parse_august_data(AUGUST_LIST_PATH)
    new_details, detail_diagnostics = parse_new_employee_details(AUGUST_DETAIL_PATH, schema_keys)
    full_data, merge_report = merge_full_august(april_data, august_list, new_details, schema_keys)
    validate_output(full_data, schema_keys, august_list)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(full_data, file, ensure_ascii=False, indent=2)
        file.write("\n")

    april_by_nip = {digits(employee.get("nip")): employee for employee in april_data}
    REPORT_PATH.write_text(
        render_report(full_data, merge_report, detail_diagnostics, april_by_nip),
        encoding="utf-8",
    )

    print(f"Output                : {OUTPUT_PATH.name}")
    print(f"Laporan               : {REPORT_PATH.name}")
    print(f"Total Agustus         : {len(full_data)}")
    print(f"Objek dari April      : {merge_report['copied_from_april']}")
    print(f"Objek detail baru     : {merge_report['created_from_august_detail']}")
    print(f"Gelar diperbarui      : {len(merge_report['title_fields_updated'])}")
    print(f"Pendidikan diperbarui : {len(merge_report['education_details_updated'])}")
    print(f"Riwayat pangkat beda  : {len(merge_report['rank_history_mismatches'])}")
    print(f"Riwayat jabatan beda  : {len(merge_report['job_history_mismatches'])}")


if __name__ == "__main__":
    main()
