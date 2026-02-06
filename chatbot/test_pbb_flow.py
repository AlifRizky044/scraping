import sys
import json
from unittest.mock import MagicMock

# Mock dependencies
sys.modules["joblib"] = MagicMock()
sys.modules["sklearn"] = MagicMock()
sys.modules["sklearn.metrics"] = MagicMock()
sys.modules["sklearn.metrics.pairwise"] = MagicMock()

# Mock redis module
mock_redis_module = MagicMock()
mock_redis_module.exceptions.ConnectionError = ConnectionError
mock_redis_module.exceptions.TimeoutError = TimeoutError
sys.modules["redis"] = mock_redis_module

# Mock Redis to behave like a dict
class FakeRedis:
    def __init__(self):
        self.data = {}
    
    def get(self, key):
        return self.data.get(key)
    
    def set(self, key, value, ex=None):
        self.data[key] = value

    def delete(self, key):
        if key in self.data:
            del self.data[key]

fake_redis = FakeRedis()
mock_config_redis = MagicMock()
mock_config_redis.redis_client = fake_redis
sys.modules["config.redis"] = mock_config_redis

# Mock utils to avoid Sastrawi and rapidfuzz
mock_utils = MagicMock()
mock_utils.preprocess_user_input = lambda x: x.lower() # Simple pass-through
mock_utils.init = lambda: None
sys.modules["utils"] = mock_utils

import unittest
import main # Import main module to patch functions
from main import chat, reset_context, set_context
import time

# Patch detect_faq to avoid ML magic mock issues
def mock_detect_faq(q):
    if "pbb" in q and "bayar" in q:
        return "bayar_pajak", "Jawaban Bayar PBB", 0.9
    return None, None, 0.0

main.detect_faq = mock_detect_faq


class TestBayarPBBFlow(unittest.TestCase):
    def setUp(self):
        self.user_id = "test_automator"
        reset_context(self.user_id)

    def tearDown(self):
        reset_context(self.user_id)

    def test_valid_pbb_flow(self):
        print("\n[TEST] Valid PBB Flow")
        
        # 1. Start check
        response = chat(self.user_id, "bayar pbb")
        self.assertIn("masukkan Nomor Objek Pajak (NOP)", response)
        
        # 2. Input NOP
        response = chat(self.user_id, "123456789012345678")
        self.assertIn("NOP Anda: 123456789012345678", response)
        self.assertIn("masukkan NIK", response)

        # 3. Input NIK
        response = chat(self.user_id, "1234567890123456")
        self.assertIn("masukkan Tahun Pajak", response)

        # 4. Input Tahun (New Step)
        response = chat(self.user_id, "2024")
        self.assertIn("Tahun: 2024", response)
        self.assertIn("Apakah data sudah benar", response)

        # 5. Confirm
        response = chat(self.user_id, "ya")
        self.assertIn("https://pajak.medan.go.id/bayar/pbb", response)

    def test_invalid_validation(self):
        print("\n[TEST] Invalid Inputs Validation")
        
        # Start
        chat(self.user_id, "bayar pbb")

        # Invalid NOP
        response = chat(self.user_id, "123")
        self.assertIn("NOP tidak valid", response)
        
        # Correct NOP
        chat(self.user_id, "123456789012345678")

        # Invalid NIK
        response = chat(self.user_id, "abc")
        self.assertIn("NIK tidak valid", response)

        # Correct NIK
        chat(self.user_id, "1234567890123456")

        # Invalid Tahun (Letters)
        response = chat(self.user_id, "abcd")
        self.assertIn("Tahun tidak valid", response)

        # Invalid Tahun (Digits != 4)
        response = chat(self.user_id, "24")
        self.assertIn("Tahun tidak valid", response)

        # Correct Tahun
        response = chat(self.user_id, "2023")
        self.assertIn("Tahun: 2023", response)

if __name__ == "__main__":
    unittest.main()
