import sys
import os
import pandas as pd

# Ensure we use the local files
sys.path.append(os.getcwd())

from main import detect_faq

def test_all_intents():
    print("=== Testing All Subjects (Intents) with Natural Questions ===")
    
    # Define test cases: Intent -> List of Natural Questions
    test_suite = {
        "apa_itu_bapenda": [
            "sebenernya bapenda itu apa sih?",
            "kasih tau dong fungsi bapenda medan",
            "bapenda medan tu ngurusin apa aja?"
        ],
        "jam_layanan": [
            "buka jam brp ya kantornya?",
            "besok minggu buka gak?",
            "hari ini sampe jam berapa pelayanannya?"
        ],
        "alamat_kantor": [
            "dimana alamat kantor bapenda?",
            "share loc kantornya dong",
            "kalo mau ke dinas pendapatan medan lewat mana?"
        ],
        "kontak_resmi": [
            "minta nomor wa admin dong",
            "ada call center yg bisa dihubungi?",
            "gimana cara kontak bapenda?"
        ],
        "jenis_pajak": [
            "pajak apa aja yg ada di medan?",
            "sebutin dong jenis2 pajak daerah",
            "bapenda ngurusi pajak apa aja?"
        ],
        "wajib_pajak": [
            "siapa aja yg harus bayar pajak?",
            "aku kena pajak gak ya?",
            "kriteria wajib pajak itu gimana?"
        ],
        "jatuh_tempo_umum": [
            "kapan paling lambat bayar pajak?",
            "deadline pembayaran pajak kapan?",
            "jangan sampe telat bayar, emang kapan tgl terakhir?"
        ],
        "jatuh_tempo_restoran": [
            "pajak resto kapan harus dibayar?",
            "batas akhir setor pajak restoran bulan ini?",
            "tgl berapa jatuh tempo pajak rm?"
        ],
        "pbb_cek_tagihan": [
            "gmn cara liat tagihan pbb saya?",
            "cek pbb online bisa gak?",
            "tolong cekin pbb rumah saya dong"
        ],
        "pbb_denda": [
            "kena denda brp kalo telat bayar pbb?",
            "telat pbb setahun dendanya gede gak?",
            "hitung denda pbb gimana caranya?"
        ],
        "pbb_mutasi": [
            "cara balik nama pbb gimana?",
            "mau ganti nama di sppt pbb",
            "syarat mutasi pbb apa aja?"
        ],
        "cara_bayar_umum": [
            "gimana sih cara bayar pajaknya?",
            "metode pembayaran pajak daerah",
            "bayar pajak bisa dimana aja?"
        ],
        "cara_bayar_restoran": [
            "tata cara setor pajak restoran",
            "bayar pajak resto kemana ya?",
            "proses pembayaran pajak rumah makan"
        ],
        "cara_bayar_pbb": [
            "bayar pbb lewat atm bisa?",
            "tutorial bayar pbb medan",
            "tempat pembayaran pbb terdekat"
        ],
        "bayar_online": [
            "pake gopay bisa bayar pajak gak?",
            "bayar pajak online lewat apa?",
            "ada aplikasi buat bayar pajak?"
        ],
        "pajak_restoran": [
            "jelasin dong apa itu pajak restoran",
            "pajak resto itu yg bayar siapa?",
            "tarif pajak restoran brp persen?"
        ],
        "pajak_hotel": [
            "pajak hotel itu hitungannya gimana?",
            "pengertian pajak hotel",
            "tamu hotel kena pajak gak?"
        ],
        "pajak_hiburan": [
            "pajak hiburan tu apa?",
            "tiket bioskop udah termasuk pajak hiburan?",
            "yg wajib bayar pajak hiburan siapa?"
        ],
        "pajak_parkir": [
            "tukang parkir kena pajak gak?",
            "pajak parkir itu apa sih?",
            "tarif pajak parkir medan"
        ],
        "sanksi": [
            "kalo gak bayar pajak hukumannya apa?",
            "ada sanksi pidana gak buat pengemplang pajak?",
            "akibat nunggak pajak daerah"
        ],
        "denda": [
            "apa bedanya sanksi sama denda pajak?",
            "gimana rumus hitung denda?",
            "denda pajak berlaku kapan?"
        ],
        "bayar_pajak": [
            "aku mau bayar pajak nih",
            "tolong bantu proses pembayaran",
            "mau lunasi kewajiban pajak"
        ]
    }
    
    total_tests = 0
    passed = 0
    failed_details = []

    print(f"{'INTENT':<25} | {'QUESTION':<40} | {'PREDICTED':<25} | {'SCORE':<5} | {'STATUS'}")
    print("-" * 110)

    for expected_intent, questions in test_suite.items():
        for q in questions:
            total_tests += 1
            pred_intent, _, score = detect_faq(q)
            
            is_match = (pred_intent == expected_intent)
            status = "PASS" if is_match else "FAIL"
            
            print(f"{expected_intent:<25} | {q:<40} | {str(pred_intent):<25} | {score:.2f}  | {status}")
            
            if is_match:
                passed += 1
            else:
                failed_details.append((q, expected_intent, pred_intent, score))

    print("-" * 110)
    print(f"\nFinal Result: {passed}/{total_tests} Passed ({passed/total_tests*100:.1f}%)")
    
    if failed_details:
        print("\n=== Failed Cases ===")
        for q, expected, actual, score in failed_details:
            print(f"Q: '{q}'\n   Expected: {expected}\n   Got:      {actual} ({score:.3f})")

if __name__ == "__main__":
    test_all_intents()
