import json
import logging
import os
import random
import re
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import quote

from logger import log_conversation
from utils import preprocess_user_input, init
from config.redis import redis_client

LOGGER = logging.getLogger("chatbot")
if not LOGGER.handlers:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# Optional ML dependencies; runtime should stay up even if model is unavailable.
try:
    import joblib
except Exception:  # pragma: no cover - exercised indirectly in tests
    joblib = None

try:
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # pragma: no cover - exercised indirectly in tests
    cosine_similarity = None

try:
    import redis
except Exception:  # pragma: no cover - exercised indirectly in tests
    redis = None


class ContextStoreUnavailable(RuntimeError):
    pass


PAJAK_KEYWORDS = [
    "hotel", "restoran", "hiburan", "reklame",
    "parkir", "air tanah", "pbb"
]

FAQ_THRESHOLD = 0.35
INTENT_FALLBACK_THRESHOLD = 0.6
ALLOW_INMEMORY_CONTEXT_FALLBACK = os.getenv("ALLOW_INMEMORY_CONTEXT_FALLBACK", "false").lower() == "true"
HANDOFF_WHATSAPP_NUMBER = os.getenv("HANDOFF_WHATSAPP_NUMBER", "62895622855506")

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_READY = False
MODEL_ERROR: Optional[str] = None
vectorizer = None
faq_vectors = None
faq_intents = None
answers = None
intent_model = None
INTENT_ANSWER_MAP = {}
INTENT_ANSWER_VARIANTS = {}

# CONTEXT STORE
USER_CONTEXTS = {}
PREFIX = "chatbot:ctx:"


# Initialize normalization dictionary for typo correction in all runtimes (CLI/API/tests).
init()


def load_models() -> bool:
    global MODEL_READY, MODEL_ERROR, vectorizer, faq_vectors, faq_intents, answers, intent_model, INTENT_ANSWER_MAP, INTENT_ANSWER_VARIANTS

    if MODEL_READY:
        return True

    if joblib is None or cosine_similarity is None:
        MODEL_ERROR = "ML dependencies unavailable (joblib/scikit-learn)."
        return False

    try:
        vectorizer = joblib.load(MODEL_DIR / "vectorizer.pkl")
        faq_vectors = joblib.load(MODEL_DIR / "faq_vectors.pkl")
        faq_intents = joblib.load(MODEL_DIR / "faq_intents.pkl")
        answers = joblib.load(MODEL_DIR / "answers.pkl")
        try:
            intent_model = joblib.load(MODEL_DIR / "intent.pkl")
        except Exception:
            intent_model = None

        INTENT_ANSWER_MAP = {}
        INTENT_ANSWER_VARIANTS = {}
        for i, intent_name in enumerate(faq_intents):
            if intent_name not in INTENT_ANSWER_MAP:
                INTENT_ANSWER_MAP[intent_name] = answers[i]
            INTENT_ANSWER_VARIANTS.setdefault(intent_name, [])
            ans = str(answers[i]).strip()
            if ans and ans not in INTENT_ANSWER_VARIANTS[intent_name]:
                INTENT_ANSWER_VARIANTS[intent_name].append(ans)

        MODEL_READY = True
        MODEL_ERROR = None
        return True
    except Exception as exc:
        MODEL_ERROR = str(exc)
        MODEL_READY = False
        LOGGER.exception("Model load failed")
        return False


def _is_redis_error(exc: Exception) -> bool:
    if redis is None:
        return True
    return isinstance(exc, (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError))


def get_context(user_id):
    try:
        data = redis_client.get(PREFIX + user_id)
        return json.loads(data) if data else {}
    except Exception as exc:
        if _is_redis_error(exc) and ALLOW_INMEMORY_CONTEXT_FALLBACK:
            return USER_CONTEXTS.get(user_id, {})
        raise ContextStoreUnavailable("Context backend unavailable") from exc


def set_context(user_id, **kwargs):
    ctx = get_context(user_id)
    ctx.update(kwargs)
    try:
        redis_client.set(PREFIX + user_id, json.dumps(ctx), ex=1800)
    except Exception as exc:
        if _is_redis_error(exc) and ALLOW_INMEMORY_CONTEXT_FALLBACK:
            USER_CONTEXTS[user_id] = ctx
            return
        raise ContextStoreUnavailable("Context backend unavailable") from exc


def reset_context(user_id):
    try:
        redis_client.delete(PREFIX + user_id)
    except Exception as exc:
        if not (_is_redis_error(exc) and ALLOW_INMEMORY_CONTEXT_FALLBACK):
            LOGGER.warning("Failed to clear redis context for user_id=%s: %s", user_id, exc)
    USER_CONTEXTS.pop(user_id, None)


def get_nop(text):
    match = re.search(r"\b\d{18}\b", text)
    return match.group() if match else None


def get_npwpd(text):
    match = re.search(r"\b\d{16}\b", text)
    return match.group() if match else None


def get_nik(text):
    match = re.search(r"\b\d{16}\b", text)
    return match.group() if match else None


def get_nib(text):
    match = re.search(r"\b\d{13}\b", text)
    return match.group() if match else None


def detect_pajaks(text):
    text = text.lower()
    return [p for p in PAJAK_KEYWORDS if p in text]


def _answer_for(intent_name):
    variants = INTENT_ANSWER_VARIANTS.get(intent_name) or []
    if variants:
        return random.choice(variants)
    return INTENT_ANSWER_MAP.get(intent_name)


def _answer_for_keyword(intent_name: str, keyword: str) -> Optional[str]:
    variants = INTENT_ANSWER_VARIANTS.get(intent_name) or []
    kw = keyword.lower()
    for ans in variants:
        if kw in ans.lower():
            return ans
    return INTENT_ANSWER_MAP.get(intent_name)


def _style_faq_answer(intent_name: str, answer: Optional[str]) -> str:
    if not answer:
        return ""

    # Keep long/multiline/link-heavy answers unchanged for clarity.
    if "\n" in answer or "http://" in answer or "https://" in answer:
        return answer

    # Keep transactional intent response stable.
    if intent_name == "bayar_pajak":
        return answer

    prefixes = [
        "",
        "Baik, ",
        "Siap, ",
        "Info singkat: ",
    ]
    return f"{random.choice(prefixes)}{answer}"


def _is_transaction_intent(q):
    if not re.search(r"\b(bayar|lunasi|setor)\b", q):
        return False
    if re.search(r"\b(cara|bagaimana|gimana|metode|dimana|tutorial)\b", q):
        return False
    return True


def _is_yes(text: str) -> bool:
    cleaned = re.sub(r"[^a-z]", "", text.strip().lower())
    return cleaned in {"ya", "iya", "yes", "y"}


def _is_no(text: str) -> bool:
    cleaned = re.sub(r"[^a-z]", "", text.strip().lower())
    return cleaned in {"tidak", "nggak", "enggak", "ga", "gak", "no", "n"}


def _handoff_offer_message() -> str:
    return (
        "Mohon maaf, saya belum dapat memahami maksud pertanyaan Anda dengan baik. "
        "Pengetahuan saya masih terbatas pada topik dan pola pertanyaan tertentu.\n"
        "Apabila Anda berkenan, saya dapat menyiapkan tautan WhatsApp agar pertanyaan ini "
        "dapat diteruskan kepada petugas kami.\n"
        "➡ ketik 'ya' untuk lanjut ke WhatsApp\n"
        "➡ ketik 'tidak' untuk kembali ke awal"
    )


def _normalized_whatsapp_number() -> str:
    return re.sub(r"\D", "", HANDOFF_WHATSAPP_NUMBER)


def _build_handoff_whatsapp_url(question: str) -> str:
    prepared_message = (
        "Halo Bapak/Ibu Petugas BAPENDA Medan,\n"
        "saya ingin bertanya pertanyaan berikut:\n\n"
        f"{question.strip()}"
    )
    phone_number = _normalized_whatsapp_number()
    return f"https://api.whatsapp.com/send?phone={phone_number}&text={quote(prepared_message)}"


def detect_faq(question: str) -> Tuple[Optional[str], Optional[str], float]:
    q_lower = question.lower()

    if not load_models():
        return None, None, 0.0

    # High-priority rule overrides for known confusing patterns.
    if re.search(r"\b(ramadhan|ramadan|puasa)\b", q_lower) and re.search(
        r"\b(jam|layanan|pelayanan|buka|tutup|kerja)\b", q_lower
    ):
        ans = _answer_for_keyword("jam_layanan", "ramadhan")
        if ans:
            return "jam_layanan", ans, 0.99
    if "pbb" in q_lower and re.search(r"\b(call|center|cs|kontak|nomor|telepon|whatsapp|wa)\b", q_lower):
        ans = _answer_for("call_center_pbb")
        if ans:
            return "call_center_pbb", ans, 0.99
    if "bphtb" in q_lower and re.search(r"\b(call|center|cs|kontak|nomor|telepon|whatsapp|wa)\b", q_lower):
        ans = _answer_for("call_center_bphtb")
        if ans:
            return "call_center_bphtb", ans, 0.99
    if "bapenda" in q_lower and re.search(r"\b(skm|survei|survey|kepuasan|feedback)\b", q_lower):
        ans = _answer_for("skm_bapenda")
        if ans:
            return "skm_bapenda", ans, 0.99
    if re.search(r"\b(lapor|keluhan|ngadu|aduan)\b", q_lower) and re.search(r"\b(pajak|layanan|bapenda)\b", q_lower):
        ans = _answer_for("pengaduan_layanan")
        if ans:
            return "pengaduan_layanan", ans, 0.99
    if "bapenda" in q_lower and re.search(r"\b(call|center|cs|kontak|nomor|telepon|whatsapp|wa)\b", q_lower):
        ans = _answer_for("kontak_resmi")
        if ans:
            return "kontak_resmi", ans, 0.99
    if "bapenda" in q_lower and re.search(r"\b(alamat|lokasi|kantor|rute)\b", q_lower):
        ans = _answer_for("alamat_kantor")
        if ans:
            return "alamat_kantor", ans, 0.99
    if "kantor" in q_lower and re.search(r"\b(dimana|dmn|alamat|lokasi|rute|arah|kantornya)\b", q_lower):
        ans = _answer_for("alamat_kantor")
        if ans:
            return "alamat_kantor", ans, 0.99
    if "pbb" in q_lower and "denda" in q_lower:
        ans = _answer_for("pbb_denda")
        if ans:
            return "pbb_denda", ans, 0.99
    if "pbb" in q_lower and re.search(r"\b(cek|tagihan|periksa)\b", q_lower):
        ans = _answer_for("pbb_cek_tagihan")
        if ans:
            return "pbb_cek_tagihan", ans, 0.99
    if (
        "hiburan" in q_lower
        and re.search(r"\b(apa|pengertian|itu|jelasin)\b", q_lower)
        and not re.search(r"\b(syarat|permohonan|daftar|tarif|wajib)\b", q_lower)
    ):
        ans = _answer_for("pajak_hiburan")
        if ans:
            return "pajak_hiburan", ans, 0.99
    if "hiburan" in q_lower and re.search(r"\b(wajib|tarif|objek|dikenakan)\b", q_lower):
        ans = _answer_for("pajak_hiburan")
        if ans:
            return "pajak_hiburan", ans, 0.99
    if "bphtb" in q_lower and "syarat" in q_lower:
        ans = _answer_for("syarat_permohonan_bphtb")
        if ans:
            return "syarat_permohonan_bphtb", ans, 0.99
    if "online" in q_lower and "bayar" in q_lower and "pajak" in q_lower:
        ans = _answer_for("bayar_online")
        if ans:
            return "bayar_online", ans, 0.99
    if re.search(r"\b(cara|bagaimana|gimana|metode)\b", q_lower) and "bayar" in q_lower:
        if not re.search(r"\b(pbb|bphtb|restoran|hotel|hiburan|parkir|reklame|air tanah)\b", q_lower):
            if re.search(r"\b(jatuh tempo|deadline|batas waktu|kapan)\b", q_lower):
                pass
            else:
                ans = _answer_for("cara_bayar_umum")
                if ans:
                    return "cara_bayar_umum", ans, 0.99
    if re.search(r"\b(syarat|permohonan|daftar|pendaftaran)\b", q_lower) and re.search(
        r"\b(hotel|restoran|hiburan)\b", q_lower
    ):
        ans = _answer_for("syarat_permohonan_hrh")
        if ans:
            return "syarat_permohonan_hrh", ans, 0.99
    if re.search(r"\b(jatuh tempo|deadline|batas waktu)\b", q_lower) and "restoran" not in q_lower and "pbb" not in q_lower:
        ans = _answer_for("jatuh_tempo_umum")
        if ans:
            return "jatuh_tempo_umum", ans, 0.99
    if "jatuh tempo" in q_lower and "restoran" not in q_lower and "pbb" not in q_lower:
        ans = _answer_for("jatuh_tempo_umum")
        if ans:
            return "jatuh_tempo_umum", ans, 0.99
    if re.search(r"\b(kena pajak|wajib pajak)\b", q_lower) and not re.search(r"\b(hotel|restoran|hiburan|parkir|pbb)\b", q_lower):
        ans = _answer_for("wajib_pajak")
        if ans:
            return "wajib_pajak", ans, 0.99

    q_vec = vectorizer.transform([question])
    sim = cosine_similarity(q_vec, faq_vectors)

    idx = sim.argmax()
    score = float(sim.max())
    predicted_intent = faq_intents[idx]
    predicted_answer = answers[idx]

    if score >= FAQ_THRESHOLD:
        if predicted_intent == "call_center_pbb" and "pbb" not in q_lower:
            pass
        elif predicted_intent == "call_center_bphtb" and "bphtb" not in q_lower:
            pass
        else:
            return predicted_intent, predicted_answer, score

    if intent_model is not None:
        probs = intent_model.predict_proba([question])[0]
        best_idx = probs.argmax()
        intent_score = float(probs[best_idx])
        intent_name = intent_model.classes_[best_idx]
        answer = _answer_for(intent_name)
        if answer and intent_score >= INTENT_FALLBACK_THRESHOLD:
            return intent_name, answer, intent_score

    return None, None, score


def bayarNonPBB(status, pajak, context, user_id, q, messageMentah):
    if status == "tanya_pajak":
        set_context(user_id, pajak=pajak, status="input_nop")
        return (
            "Silakan masukkan Nomor Pokok Wajib Pajak Daerah (NPWPD) untuk pajak " + pajak + ".\n"
            "Ketik 'batal' untuk keluar."
        )

    if status == "input_nop":
        nop = get_npwpd(messageMentah)
        if not nop:
            return (
                "NPWPD tidak valid.\n"
                "Silakan masukkan NPWPD yang benar.\n"
                "Ketik 'batal' untuk keluar."
            )

        set_context(user_id, status="input_nik", nop=nop)
        return (
            f"NPWPD Anda: {nop}\n"
            "Silakan masukkan NIK/NIB anda.\n"
            "Ketik 'batal' untuk keluar."
        )

    if status == "input_nik":
        nik = get_nik(messageMentah)
        nib = get_nib(messageMentah)

        if not nik and not nib:
            return (
                "NIK/NIB tidak valid.\n"
                "Silakan masukkan NIK yang benar.\n"
                "Ketik 'batal' untuk keluar."
            )

        result = nik if nik else nib
        label = "NIK" if len(result) == 16 else "NIB"

        set_context(user_id, status="input_masa", nik=result, label=label)
        return (
            f"NPWPD: {context.get('nop')}\n"
            f"{label}: {result}\n"
            "Silakan masukkan Masa Pajak (Bulan-Tahun).\n"
            "Contoh: 01-2024\n"
            "Ketik 'batal' untuk keluar."
        )

    if status == "input_masa":
        masa = messageMentah.strip()
        if not re.match(r"^(0[1-9]|1[0-2])-\d{4}$", masa):
            return (
                "Format Masa Pajak tidak valid.\n"
                "Gunakan format Bulan-Tahun (MM-YYYY), contoh: 01-2024.\n"
                "Ketik 'batal' untuk keluar."
            )

        set_context(user_id, status="konfirmasi", masa=masa)
        return (
            f"NPWPD: {context.get('nop')}\n"
            f"{context.get('label') or 'NIK/NIB'}: {context.get('nik')}\n"
            f"Masa Pajak: {masa}\n"
            "Apakah data sudah benar?\n"
            "➡ ketik 'ya' untuk lanjut\n"
            "➡ ketik 'tidak' untuk ulang\n"
            "➡ ketik 'batal' untuk keluar"
        )

    if status == "konfirmasi":
        if messageMentah.lower() == "ya":
            set_context(user_id, status="bayar_pajak")
            reset_context(user_id)
            return (
                "Silakan lanjutkan pembayaran melalui link berikut:\n"
                "https://pajak.medan.go.id/bayar/nonpbb"
            )

        if messageMentah.lower() == "tidak":
            set_context(user_id, status="input_nop")
            return (
                "Baik, kita ulang dari awal.\n"
                "Silakan masukkan Nomor Pokok Wajib Pajak Daerah (NPWPD).\nKetik 'batal' untuk keluar."
            )

        return "Silakan ketik 'ya' atau 'tidak'.\nKetik 'batal' untuk keluar."

    reset_context(user_id)
    return "Terjadi kesalahan alur. Silakan ulangi dari awal.\n Ada yang bisa saya bantu lagi?"


def bayarPBB(status, context, user_id, q, messageMentah):
    if status == "tanya_pajak":
        set_context(user_id, pajak="pbb", status="input_nop")
        return (
            "Silakan masukkan Nomor Objek Pajak (NOP).\n"
            "Ketik 'batal' untuk keluar."
        )

    if status == "input_nop":
        nop = get_nop(messageMentah)
        if not nop:
            return (
                "NOP tidak valid.\n"
                "Silakan masukkan NOP yang benar.\n"
                "Ketik 'batal' untuk keluar."
            )

        set_context(user_id, status="input_nik", nop=nop)
        return (
            f"NOP Anda: {nop}\n"
            "Silakan masukkan NIK.\n"
            "Ketik 'batal' untuk keluar."
        )

    if status == "input_nik":
        nik = get_nik(messageMentah)
        if not nik:
            return (
                "NIK tidak valid.\n"
                "Silakan masukkan NIK yang benar.\n"
                "Ketik 'batal' untuk keluar."
            )

        set_context(user_id, status="input_tahun", nik=nik)
        return (
            f"NOP: {context.get('nop')}\n"
            f"NIK: {nik}\n"
            "Silakan masukkan Tahun Pajak yang ingin dibayar (contoh: 2024).\n"
            "Ketik 'batal' untuk keluar."
        )

    if status == "input_tahun":
        tahun = messageMentah.strip()
        if not tahun.isdigit() or len(tahun) != 4:
            return (
                "Tahun tidak valid.\n"
                "Silakan masukkan tahun yang benar (4 digit).\n"
                "Ketik 'batal' untuk keluar."
            )

        set_context(user_id, status="konfirmasi", tahun=tahun)
        return (
            f"NOP: {context.get('nop')}\n"
            f"NIK: {context.get('nik')}\n"
            f"Tahun: {tahun}\n"
            "Apakah data sudah benar?\n"
            "➡ ketik 'ya' untuk lanjut\n"
            "➡ ketik 'tidak' untuk ulang\n"
            "➡ ketik 'batal' untuk keluar"
        )

    if status == "konfirmasi":
        if messageMentah.lower() == "ya":
            set_context(user_id, status="bayar_pajak")
            reset_context(user_id)
            return (
                "Silakan lanjutkan pembayaran melalui link berikut:\n"
                "https://pajak.medan.go.id/bayar/pbb"
            )

        if messageMentah.lower() == "tidak":
            set_context(user_id, status="input_nop")
            return (
                "Baik, kita ulang dari awal.\n"
                "Silakan masukkan Nomor Objek Pajak (NOP).\nKetik 'batal' untuk keluar."
            )

        return "Silakan ketik 'ya' atau 'tidak'.\nKetik 'batal' untuk keluar."

    reset_context(user_id)
    return "Terjadi kesalahan alur. Silakan ulangi dari awal.\n Ada yang bisa saya bantu lagi?"


def chat(user_id: str, message: str) -> str:
    q = preprocess_user_input(message)
    messageMentah = message

    def reply(msg, intent="UNKNOWN", score=0.0, successful=True):
        if not successful:
            safe_intent = intent if intent else "NONE"
            log_conversation(user_id, message, safe_intent, score, msg)
        return msg

    try:
        ctx = get_context(user_id)
    except ContextStoreUnavailable:
        return reply(
            "Layanan sedang sibuk. Silakan coba beberapa saat lagi.",
            "CONTEXT_STORE_UNAVAILABLE",
            0.0,
            successful=False,
        )

    if ctx and (q == "batal" or messageMentah.strip().lower() == "batal"):
        reset_context(user_id)
        return reply("Transaksi dibatalkan. Ada yang bisa saya bantu lagi?", "CANCEL", 1.0, successful=True)

    try:
        if ctx:
            status = ctx.get("status")
            if status == "handoff_offer":
                if _is_yes(messageMentah):
                    original_question = str(ctx.get("handoff_question") or "").strip()
                    reset_context(user_id)
                    return reply(
                        "Baik, silakan lanjutkan melalui WhatsApp berikut. "
                        "Tautan ini sudah memuat pertanyaan Anda:\n"
                        f"{_build_handoff_whatsapp_url(original_question)}",
                        "HANDOFF_ACCEPTED",
                        1.0,
                        successful=True,
                    )

                if _is_no(messageMentah):
                    reset_context(user_id)
                    return reply(
                        "Baik, pertanyaan Anda tidak akan saya teruskan. "
                        "Percakapan saya kembalikan ke awal. "
                        "Jika ada pertanyaan lain terkait pajak, silakan sampaikan.",
                        "HANDOFF_DECLINED",
                        1.0,
                        successful=True,
                    )

                return reply(
                    "Silakan jawab dengan 'ya' jika Anda ingin saya siapkan tautan WhatsApp, "
                    "atau 'tidak' jika Anda ingin kembali ke awal.",
                    "HANDOFF_PENDING",
                    1.0,
                    successful=True,
                )

            if status == "tanya_pajak":
                pajaks = detect_pajaks(q)

                if not pajaks:
                    return reply(
                        "Maaf, jenis pajak tidak dikenali.\n"
                        "Silakan sebutkan jenis pajak atau ketik 'batal'.",
                        "FLOW_ERROR_TAX", 1.0, successful=False
                    )

                if len(pajaks) > 1:
                    return reply(
                        "Saya hanya bisa memproses satu pajak dalam satu waktu 🙏\n"
                        "Silakan pilih salah satu:\n"
                        "• Hotel\n"
                        "• Restoran\n"
                        "• Hiburan\n"
                        "• Reklame\n"
                        "• Parkir\n"
                        "• Air Tanah\n"
                        "• PBB",
                        "FLOW_AMBIGUOUS", 1.0, successful=False
                    )

                pajak = pajaks[0]
                set_context(user_id, pajak=pajak)
                ctx["pajak"] = pajak

            pajak = ctx.get("pajak")

            if pajak in PAJAK_KEYWORDS and pajak != "pbb":
                return reply(bayarNonPBB(status, pajak, ctx, user_id, q, messageMentah), f"FLOW_{pajak.upper()}", 1.0, successful=True)

            if pajak == "pbb":
                return reply(bayarPBB(status, ctx, user_id, q, messageMentah), "FLOW_PBB", 1.0, successful=True)

        intent, answer, score = detect_faq(q)
        LOGGER.info("detect_faq intent=%s score=%.3f", intent, score)

        if _is_transaction_intent(q):
            pajaks = detect_pajaks(q)
            if len(pajaks) == 1:
                pajak = pajaks[0]
                if pajak == "pbb":
                    set_context(user_id, status="input_nop", pajak=pajak)
                    return reply(
                        "Silakan masukkan Nomor Objek Pajak (NOP).\n"
                        "Ketik 'batal' untuk keluar.",
                        "FLOW_PBB",
                        1.0,
                        successful=True,
                    )
                set_context(user_id, status="input_nop", pajak=pajak)
                return reply(
                    "Silakan masukkan Nomor Pokok Wajib Pajak Daerah (NPWPD).\n"
                    "Ketik 'batal' untuk keluar.",
                    f"FLOW_{pajak.upper()}",
                    1.0,
                    successful=True,
                )
            if len(pajaks) > 1:
                set_context(user_id, status="tanya_pajak")
                return reply(
                    "Saya hanya bisa memproses satu pajak dalam satu waktu 🙏\n"
                    "Silakan pilih salah satu:\n"
                    "• Hotel\n"
                    "• Restoran\n"
                    "• Hiburan\n"
                    "• Reklame\n"
                    "• Parkir\n"
                    "• Air Tanah\n"
                    "• PBB",
                    "FLOW_AMBIGUOUS",
                    1.0,
                    successful=False,
                )

        if intent == "bayar_pajak":
            pajaks = detect_pajaks(q)

            if not pajaks:
                set_context(user_id, status="tanya_pajak")
                return reply("Baik, mau bayar pajak apa? (contoh: restoran, PBB, hotel)", intent, score, successful=True)

            if len(pajaks) > 1:
                set_context(user_id, status="tanya_pajak")
                return reply(
                    "Saya hanya bisa memproses satu pajak dalam satu waktu 🙏\n"
                    "Silakan pilih salah satu:\n"
                    "• Hotel\n"
                    "• Restoran\n"
                    "• Hiburan\n"
                    "• Reklame\n"
                    "• Parkir\n"
                    "• Air Tanah\n"
                    "• PBB",
                    intent, score, successful=False
                )

            pajak = pajaks[0]
            if pajak and pajak != "pbb":
                set_context(user_id, status="input_nop", pajak=pajak)
                return reply(
                    "Silakan masukkan Nomor Pokok Wajib Pajak Daerah (NPWPD).\n"
                    "Ketik 'batal' untuk keluar.",
                    intent, score, successful=True
                )

            if pajak == "pbb":
                set_context(user_id, status="input_nop", pajak=pajak)
                return reply(
                    "Silakan masukkan Nomor Objek Pajak (NOP).\n"
                    "Ketik 'batal' untuk keluar.",
                    intent, score, successful=True
                )

            set_context(user_id, status="tanya_pajak")
            return reply("Baik, mau bayar pajak apa? (contoh: restoran, PBB, hotel)", intent, score, successful=True)

        if not intent:
            set_context(user_id, status="handoff_offer", handoff_question=messageMentah.strip())
            return reply(_handoff_offer_message(), "NO_INTENT", 0.0, successful=False)

        return reply(_style_faq_answer(intent, answer), intent, score, successful=True)
    except ContextStoreUnavailable:
        return reply(
            "Layanan sedang sibuk. Silakan coba beberapa saat lagi.",
            "CONTEXT_STORE_UNAVAILABLE",
            0.0,
            successful=False,
        )


def get_runtime_status() -> dict:
    model_ready = load_models()
    redis_ok = True
    redis_error = None
    try:
        redis_client.ping()
    except Exception as exc:
        redis_ok = False
        redis_error = str(exc)

    return {
        "model_ready": model_ready,
        "model_error": MODEL_ERROR,
        "redis_ok": redis_ok,
        "redis_error": redis_error,
        "allow_inmemory_fallback": ALLOW_INMEMORY_CONTEXT_FALLBACK,
    }


# Attempt model warm-up at import time; failure is reflected by readiness endpoint.
load_models()


if __name__ == "__main__":
    user_id = "test_user"
    reset_context(user_id)
    while True:
        q = input("Anda: ")
        if q.lower() in ["exit", "quit"]:
            break
        print("AI :", chat(user_id, q))
