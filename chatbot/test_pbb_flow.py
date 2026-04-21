import unittest
from unittest.mock import patch

from main import chat, reset_context


def mock_detect_faq(q):
    if "pbb" in q and "bayar" in q:
        return "bayar_pajak", "Jawaban Bayar PBB", 0.9
    return None, None, 0.0


class TestBayarPBBFlow(unittest.TestCase):
    def setUp(self):
        self.user_id = "test_automator"
        reset_context(self.user_id)
        self.detect_faq_patcher = patch("main.detect_faq", side_effect=mock_detect_faq)
        self.detect_faq_patcher.start()

    def tearDown(self):
        self.detect_faq_patcher.stop()
        reset_context(self.user_id)

    def test_valid_pbb_flow(self):
        response = chat(self.user_id, "bayar pbb")
        self.assertIn("masukkan Nomor Objek Pajak (NOP)", response)

        response = chat(self.user_id, "123456789012345678")
        self.assertIn("NOP Anda: 123456789012345678", response)
        self.assertIn("masukkan NIK", response)

        response = chat(self.user_id, "1234567890123456")
        self.assertIn("masukkan Tahun Pajak", response)

        response = chat(self.user_id, "2024")
        self.assertIn("Tahun: 2024", response)
        self.assertIn("Apakah data sudah benar", response)

        response = chat(self.user_id, "ya")
        self.assertIn("https://pajak.medan.go.id/bayar/pbb", response)

    def test_invalid_validation(self):
        chat(self.user_id, "bayar pbb")

        response = chat(self.user_id, "123")
        self.assertIn("NOP tidak valid", response)

        chat(self.user_id, "123456789012345678")

        response = chat(self.user_id, "abc")
        self.assertIn("NIK tidak valid", response)

        chat(self.user_id, "1234567890123456")

        response = chat(self.user_id, "abcd")
        self.assertIn("Tahun tidak valid", response)

        response = chat(self.user_id, "24")
        self.assertIn("Tahun tidak valid", response)

        response = chat(self.user_id, "2023")
        self.assertIn("Tahun: 2023", response)


if __name__ == "__main__":
    unittest.main()
