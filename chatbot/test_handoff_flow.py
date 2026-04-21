import unittest
from unittest.mock import patch
from urllib.parse import quote

import main
from main import chat, get_context, reset_context


def mock_detect_faq(_):
    return None, None, 0.0


class TestHandoffFlow(unittest.TestCase):
    def setUp(self):
        self.user_id = "test_handoff"
        self.allow_fallback_patcher = patch.object(main, "ALLOW_INMEMORY_CONTEXT_FALLBACK", True)
        self.detect_faq_patcher = patch("main.detect_faq", side_effect=mock_detect_faq)
        self.allow_fallback_patcher.start()
        self.detect_faq_patcher.start()
        reset_context(self.user_id)

    def tearDown(self):
        self.detect_faq_patcher.stop()
        self.allow_fallback_patcher.stop()
        reset_context(self.user_id)

    def test_unknown_question_offers_handoff(self):
        response = chat(self.user_id, "resep nasi goreng")

        self.assertIn("belum dapat memahami maksud pertanyaan Anda", response)
        self.assertIn("tautan WhatsApp", response)
        self.assertIn("ketik 'ya'", response)
        self.assertEqual(get_context(self.user_id).get("status"), "handoff_offer")

    def test_accept_handoff_redirects_to_whatsapp(self):
        chat(self.user_id, "resep nasi goreng")
        response = chat(self.user_id, "ya")

        self.assertIn("https://api.whatsapp.com/send?phone=62895622855506&text=", response)
        self.assertIn(quote("resep nasi goreng"), response)
        self.assertEqual(get_context(self.user_id), {})

    def test_decline_handoff_resets_to_initial_state(self):
        chat(self.user_id, "resep nasi goreng")
        response = chat(self.user_id, "tidak")

        self.assertIn("tidak akan saya teruskan", response)
        self.assertIn("kembalikan ke awal", response)
        self.assertEqual(get_context(self.user_id), {})


if __name__ == "__main__":
    unittest.main()
