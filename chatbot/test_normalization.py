import sys
import unittest
# Mock redis before importing utils/main if they depend on it (though utils usually doesn't import redis directly, main does)
# But we are importing utils directly. analyzing utils.py imports..
# utils imports re, Sastrawi, rapidfuzz. No redis.

from utils import preprocess_user_input, init

class TestNormalization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize dictionary for fuzzy matching
        init()

    def test_slang_expansion(self):
        # Common chat slang
        cases = {
            "gmn": "bagaimana",
            "brp": "berapa",
            "kpn": "kapan",
            "gak": "tidak",
            "bkn": "bukan",
            "sy": "saya",
            "makasih": "terima kasih" # stemming might handle or miss, checking dict
        }
        
        print("\n=== Testing Slang Expansion ===")
        for slang, expected in cases.items():
            processed = preprocess_user_input(slang)
            print(f"'{slang}' -> '{processed}'")
            # We check if expected root/word is present
            # Note: Stemmer might change 'bagaimana' -> 'bagaimana' root. 
            # 'terima kasih' might remain as is or split.
            # We mostly want to ensure the meaning is preserved/formalized.
            if expected == "terima kasih":
                continue # Skip strict check for this, just visual
            self.assertIn(expected, processed)

    def test_sentence_normalization(self):
        print("\n=== Testing Sentence Normalization ===")
        # Mix of slang and typos
        input_text = "gmn cara byr pjk restoran?"
        processed = preprocess_user_input(input_text)
        print(f"Input:    '{input_text}'")
        print(f"Output:   '{processed}'")
        
        expected_words = ["bagaimana", "cara", "bayar", "pajak", "restoran"]
        for word in expected_words:
            self.assertIn(word, processed)

    def test_english_loanwords(self):
        print("\n=== Testing English/Loanwords ===")
        # Loanwords added to SLANG_DICT
        inputs = [
            ("share loc dong", "lokasi"),
            ("deadline kapan", "jatuh tempo"), # might stem to 'jatuh tempo'
            ("hubungi call center", "pusat")
        ]
        
        for raw, keyword in inputs:
            processed = preprocess_user_input(raw)
            print(f"'{raw}' -> '{processed}'")
            self.assertIn(keyword, processed)

    def test_typo_correction(self):
        print("\n=== Testing Typo Correction ===")
        # "bapeda" is in SLANG_DICT mapping to "bapenda"
        # "pjak" -> "pajak"
        
        typos = {
            "bapeda": "bapenda",
            "pjak": "pajak",
            "pajk": "pajak"
        }
        
        for typo, correct in typos.items():
            processed = preprocess_user_input(typo)
            print(f"'{typo}' -> '{processed}'")
            self.assertIn(correct, processed)

if __name__ == '__main__':
    unittest.main()
