import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from main import detect_faq
from utils import init, preprocess_user_input


@dataclass
class Case:
    text: str
    expected_intent: str


INTENT_GROUPS = {
    "kontak_layanan": {"kontak_resmi", "pengaduan_layanan"},
    "jatuh_tempo": {"jatuh_tempo_umum", "jatuh_tempo_restoran"},
    "sanksi_denda": {"sanksi", "denda", "pbb_denda"},
    "bayar_info": {"bayar_pajak", "cara_bayar_umum"},
    "pbb_permohonan": {"syarat_permohonan_pbb", "standar_pelayanan_pbb"},
    "syarat_umum_hrh": {"syarat_permohonan_umum", "syarat_permohonan_hrh"},
}

INTENT_TO_GROUP = {}
for group_name, intents in INTENT_GROUPS.items():
    for intent_name in intents:
        INTENT_TO_GROUP[intent_name] = group_name


def canonical_intent(intent: str) -> str:
    return INTENT_TO_GROUP.get(intent, intent)


def build_cases() -> List[Case]:
    return [
        Case("bapenda tu apa sih sebenernya", "apa_itu_bapenda"),
        Case("fungsi bapenda apa aja bang", "tugas_fungsi"),
        Case("kantor bapenda di mana ya", "alamat_kantor"),
        Case("ada nomor wa bapenda ga", "kontak_resmi"),
        Case("jam buka kantor sampe jam brp", "jam_layanan"),
        Case("jenis pajak daerah apa aja min", "jenis_pajak"),
        Case("siapa aja yang kena wajib pajak", "wajib_pajak"),
        Case("kalo telat bayar ada sanksi ga", "sanksi"),
        Case("denda pajak itu hitungnya gimana", "denda"),
        Case("deadline bayar pajak kapan", "jatuh_tempo_umum"),
        Case("jatuh tempo pajak resto kapan ya", "jatuh_tempo_restoran"),
        Case("cek tagihan pbb lewat mana", "pbb_cek_tagihan"),
        Case("denda pbb kalo telat berapa", "pbb_denda"),
        Case("mau balik nama pbb gimana", "pbb_mutasi"),
        Case("cara bayar pajak daerah gimana", "cara_bayar_umum"),
        Case("bayar pbb bisa dimana", "cara_bayar_pbb"),
        Case("bayar pajak resto kemana", "cara_bayar_restoran"),
        Case("bisa bayar pajak online ga", "bayar_online"),
        Case("pajak restoran itu apa", "pajak_restoran"),
        Case("pajak hotel itu apa", "pajak_hotel"),
        Case("pajak hiburan itu apa", "pajak_hiburan"),
        Case("pajak parkir itu apa sih", "pajak_parkir"),
        Case("aku mau bayar pajak nih", "bayar_pajak"),
        Case("mau bayar pajak", "bayar_pajak"),
        Case("cara bayar gmn", "cara_bayar_umum"),
        Case("call center pbb nomor brp", "call_center_pbb"),
        Case("nomor cs bphtb berapa", "call_center_bphtb"),
        Case("syarat bphtb jual beli apa aja", "syarat_permohonan_bphtb"),
        Case("syarat pbb baru apa aja", "syarat_permohonan_pbb"),
        Case("syarat daftar pajak reklame apa", "syarat_permohonan_reklame"),
        Case("syarat daftar pajak restoran apa", "syarat_permohonan_hrh"),
        Case("cara daftar npwpd parkir gimana", "syarat_permohonan_parkir"),
        Case("syarat daftar pajak air tanah apa", "syarat_permohonan_air_tanah"),
        Case("tarif bphtb medan berapa", "tarif_bphtb"),
        Case("tarif pbb p2 medan berapa", "tarif_pbb"),
        Case("alur permohonan pbb baru gimana", "standar_pelayanan_pbb"),
        Case("kalau mau ngadu layanan pajak kemana", "pengaduan_layanan"),
        Case("ada survey kepuasan masyarakat bapenda", "skm_bapenda"),
        Case("mau tanya pajak dong", "tanya_faq"),
        Case("mau tanya pbb", "tanya_faq"),
        Case("bayar pke ovo bisa?", "bayar_online"),
        Case("bisa bayar pake gopay ga", "bayar_online"),
        Case("gmn cara cek pbb onlen", "pbb_cek_tagihan"),
        Case("kena denda brp kalo telat pbb", "pbb_denda"),
        Case("buat daftar pajak hiburan syaratnya", "syarat_permohonan_hrh"),
        Case("yg wajib bayar pajak hiburan siapa", "pajak_hiburan"),
        Case("tarif pajak hiburan berapa", "pajak_hiburan"),
        Case("lokasi kantor bapenda share dong", "alamat_kantor"),
        Case("kontak pengaduan bapenda dimana", "kontak_resmi"),
        Case("jam pelayanan pas ramadhan gimana", "jam_layanan"),
    ]


def run(cases: List[Case]) -> Dict:
    details = []
    passed = 0
    for case in cases:
        normalized = preprocess_user_input(case.text)
        predicted, _, score = detect_faq(normalized)
        ok = canonical_intent(predicted or "NONE") == canonical_intent(case.expected_intent)
        if ok:
            passed += 1
        details.append(
            {
                "text": case.text,
                "normalized": normalized,
                "expected": case.expected_intent,
                "predicted": predicted,
                "score": float(score),
                "pass": ok,
            }
        )
    total = len(cases)
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": (passed / total * 100.0) if total else 0.0,
        "details": details,
    }


def main():
    init()
    cases = build_cases()
    report = run(cases)

    print("=== Chatty User Query Test ===")
    print(f"Accuracy: {report['passed']}/{report['total']} ({report['accuracy']:.2f}%)")

    failed = [d for d in report["details"] if not d["pass"]]
    if failed:
        print("\nFailed cases:")
        for row in failed:
            print(
                f"- {row['text']} -> expected={row['expected']} "
                f"got={row['predicted']} score={row['score']:.3f}"
            )
    else:
        print("\nNo failed cases.")

    out = Path("logs/chatty_user_queries_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport saved: {out}")


if __name__ == "__main__":
    main()
