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

# Mock redis module
mock_redis_module = MagicMock()
mock_redis_module.exceptions.ConnectionError = ConnectionError
mock_redis_module.exceptions.TimeoutError = TimeoutError
sys.modules["redis"] = mock_redis_module

# Mock Redis class logic
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

# Mock utils
mock_utils = MagicMock()
mock_utils.preprocess_user_input = lambda x: x.lower()
mock_utils.init = lambda: None
sys.modules["utils"] = mock_utils

import unittest
import main
from main import chat, reset_context

# Patch detect_faq
def mock_detect_faq(q):
    if "pajak" in q and "bayar" in q:
        return "bayar_pajak", "Jawaban Bayar Pajak", 0.9
    return None, None, 0.0
main.detect_faq = mock_detect_faq

class TestNonPBBFlow(unittest.TestCase):
    def setUp(self):
        self.user_id = "test_non_pbb"
        reset_context(self.user_id)

    def tearDown(self):
        reset_context(self.user_id)

    def test_valid_flow(self):
        print("\n[TEST] Valid Non-PBB Flow (Restoran)")
        
        # 1. Start intent
        response = chat(self.user_id, "aku mau bayar pajak")
        self.assertIn("mau bayar pajak apa", response)

        # 2. Select Tax Type
        response = chat(self.user_id, "restoran")
        self.assertIn("masukkan Nomor Pokok Wajib Pajak Daerah", response)

        # 3. Input NPWPD
        response = chat(self.user_id, "1234567890123456")
        self.assertIn("NPWPD Anda: 1234567890123456", response)
        self.assertIn("masukkan NIK/NIB", response)

        # 4. Input NIK
        response = chat(self.user_id, "1234567890123456")
        self.assertIn("Masa Pajak", response)
        self.assertIn("Bulan-Tahun", response)

        # 5. Input Masa (Invalid)
        response = chat(self.user_id, "13-2024") # Invalid month
        self.assertIn("Format Masa Pajak tidak valid", response)

        # 6. Input Masa (Valid)
        response = chat(self.user_id, "05-2024")
        self.assertIn("Masa Pajak: 05-2024", response)
        self.assertIn("Apakah data sudah benar", response)

        # 7. Confirm
        response = chat(self.user_id, "ya")
        self.assertIn("https://pajak.medan.go.id/bayar/nonpbb", response)

if __name__ == "__main__":
    unittest.main()
