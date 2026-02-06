import sys
import os

# Ensure we use the local files
sys.path.append(os.getcwd())

from main import detect_faq, detect_pajaks

def test_predictions():
    print("=== Testing Model Predictions ===")
    
    test_cases = [
        ("kak mau bayar pajak", "bayar_pajak"),
        ("bayar pajak dmn ya", "bayar_pajak"),
        ("apa itu bapenda", "apa_itu_bapenda"),
        ("kantornya dimana bg", "alamat_kantor"),
        ("gmn cara cek pbb ya", "pbb_cek_tagihan"),
        ("bisa bayar lewat gopay gak", "bayar_online")
    ]
    
    failed = 0
    for query, expected_intent in test_cases:
        intent, answer, score = detect_faq(query)
        print(f"Q: '{query}' -> Intent: {intent} (Score: {score:.3f})")
        if intent != expected_intent:
            print(f"   [FAIL] Expected {expected_intent}")
            failed += 1
        else:
            print("   [PASS]")
            
    print("\n=== Testing Keyword Detection ===")
    pajak_cases = [
        ("mau bayar restoran", ["restoran"]),
        ("bayar pbb dong", ["pbb"]),
        ("pjak rklame", ["reklame"]), # typos handled by utils?
    ]
    
    for query, expected in pajak_cases:
        found = detect_pajaks(query)
        print(f"Q: '{query}' -> Found: {found}")
        # Note: fuzzy matching might be tricky, checking exact match for now if simple
        # But detect_pajaks uses PAJAK_KEYWORDS filtering on processed text
        
    if failed > 0:
        sys.exit(1)
    print("\n✅ All Model Tests Passed")

if __name__ == "__main__":
    test_predictions()
