import joblib
import re
from sklearn.metrics.pairwise import cosine_similarity
from utils import preprocess_user_input, init
from logger import log_conversation
from config.redis import redis_client
import json

# LOAD MODELS
vectorizer = joblib.load("models/vectorizer.pkl")
faq_vectors = joblib.load("models/faq_vectors.pkl")
faq_intents = joblib.load("models/faq_intents.pkl")
answers = joblib.load("models/answers.pkl")
try:
    intent_model = joblib.load("models/intent.pkl")
except Exception:
    intent_model = None

PAJAK_KEYWORDS = [
    "hotel", "restoran", "hiburan", "reklame",
    "parkir", "air tanah", "pbb"
]

FAQ_THRESHOLD = 0.35
INTENT_FALLBACK_THRESHOLD = 0.6

INTENT_ANSWER_MAP = {}
for i, intent_name in enumerate(faq_intents):
    if intent_name not in INTENT_ANSWER_MAP:
        INTENT_ANSWER_MAP[intent_name] = answers[i]

# Initialize normalization dictionary for typo correction in all runtimes (CLI/API/tests).
init()

import redis

# ======================================================
# CONTEXT STORE (MULTI USER - IN MEMORY FALLBACK)
# ======================================================
USER_CONTEXTS = {}
PREFIX = "chatbot:ctx:"

def get_context(user_id):
    try:
        data = redis_client.get(PREFIX + user_id)
        return json.loads(data) if data else {}
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        # Fallback to in-memory
        return USER_CONTEXTS.get(user_id, {})

def set_context(user_id, **kwargs):
    ctx = get_context(user_id)
    ctx.update(kwargs)
    try:
        redis_client.set(PREFIX + user_id, json.dumps(ctx), ex=1800)
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        # Fallback to in-memory
        USER_CONTEXTS[user_id] = ctx

def reset_context(user_id):
    try:
        redis_client.delete(PREFIX + user_id)
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        pass
    # Always clear in-memory fallback too just in case
    if user_id in USER_CONTEXTS:
        del USER_CONTEXTS[user_id]

# def get_context(user_id):
#     return USER_CONTEXTS.setdefault(user_id, {})

# def set_context(user_id, **kwargs):
#     ctx = get_context(user_id)
#     ctx.update(kwargs)

# def reset_context(user_id):
#     USER_CONTEXTS.pop(user_id, None)


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

# def detect_pajak(text):
#     text = text.lower()
#     for p in PAJAK_KEYWORDS:
#         if p in text:
#             return p
#     return None

def detect_pajaks(text):
    text = text.lower()
    found = [p for p in PAJAK_KEYWORDS if p in text]
    return found

def _answer_for(intent_name):
    return INTENT_ANSWER_MAP.get(intent_name)

def _is_transaction_intent(q):
    if not re.search(r"\b(bayar|lunasi|setor)\b", q):
        return False
    # Kalau user bertanya cara/metode, anggap FAQ informatif.
    if re.search(r"\b(cara|bagaimana|gimana|metode|dimana|tutorial)\b", q):
        return False
    return True


def detect_faq(question):
    q_lower = question.lower()

    # High-priority rule overrides for known confusing patterns.
    if "bphtb" in q_lower and re.search(r"\b(call|center|cs|kontak|nomor)\b", q_lower):
        ans = _answer_for("call_center_bphtb")
        if ans:
            return "call_center_bphtb", ans, 0.99
    if "pbb" in q_lower and "denda" in q_lower:
        ans = _answer_for("pbb_denda")
        if ans:
            return "pbb_denda", ans, 0.99
    if "pbb" in q_lower and re.search(r"\b(cek|tagihan|periksa)\b", q_lower):
        ans = _answer_for("pbb_cek_tagihan")
        if ans:
            return "pbb_cek_tagihan", ans, 0.99
    if "hiburan" in q_lower and re.search(r"\b(apa|pengertian)\b", q_lower):
        ans = _answer_for("pajak_hiburan")
        if ans:
            return "pajak_hiburan", ans, 0.99
    if "bphtb" in q_lower and "syarat" in q_lower:
        ans = _answer_for("syarat_permohonan_bphtb")
        if ans:
            return "syarat_permohonan_bphtb", ans, 0.99
    if "jatuh tempo" in q_lower and "restoran" not in q_lower and "pbb" not in q_lower:
        ans = _answer_for("jatuh_tempo_umum")
        if ans:
            return "jatuh_tempo_umum", ans, 0.99

    q_vec = vectorizer.transform([question])
    sim = cosine_similarity(q_vec, faq_vectors)

    idx = sim.argmax()
    score = sim.max()
    predicted_intent = faq_intents[idx]
    predicted_answer = answers[idx]

    if score >= FAQ_THRESHOLD:
        # Avoid overfitting "call center" intents on generic contact queries.
        if predicted_intent == "call_center_pbb" and "pbb" not in q_lower:
            pass
        elif predicted_intent == "call_center_bphtb" and "bphtb" not in q_lower:
            pass
        else:
            return predicted_intent, predicted_answer, score

    # Fallback multiclass intent model for broader intent generalization.
    if intent_model is not None:
        probs = intent_model.predict_proba([question])[0]
        best_idx = probs.argmax()
        intent_score = float(probs[best_idx])
        intent_name = intent_model.classes_[best_idx]
        answer = INTENT_ANSWER_MAP.get(intent_name)
        if answer and intent_score >= INTENT_FALLBACK_THRESHOLD:
            return intent_name, answer, intent_score

    return None, None, score

def bayarNonPBB(status, pajak, context, user_id, q, messageMentah):
    # 🔹 TANYA JENIS PAJAK
    if status == "tanya_pajak":
        set_context(user_id, pajak=pajak, status="input_nop")
        return (
            "Silakan masukkan Nomor Pokok Wajib Pajak Daerah (NPWPD) untuk pajak " + pajak + ".\n"
            "Ketik 'batal' untuk keluar."
        )

    # 🔹 INPUT NOP
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

    # 🔹 INPUT NIK
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

        if(len(result) == 16):
            label = "NIK"
        else:
            label = "NIB"

        set_context(user_id, status="input_masa", nik=result, label=label)
        return (
            f"NPWPD: {context.get('nop')}\n"
            f"{label}: {result}\n"
            "Silakan masukkan Masa Pajak (Bulan-Tahun).\n"
            "Contoh: 01-2024\n"
            "Ketik 'batal' untuk keluar."
        )

    # 🔹 INPUT MASA PAJAK
    if status == "input_masa":
        masa = messageMentah.strip()
        # Regex simple check: MM-YYYY
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

    # 🔹 KONFIRMASI
    if status == "konfirmasi":
        if messageMentah.lower() == "ya":
            set_context(user_id, status="bayar_pajak")
            reset_context(user_id)

            return (
                "Silakan lanjutkan pembayaran melalui link berikut:\n"
                "https://pajak.medan.go.id/bayar/nonpbb"
            )

        if messageMentah.lower() == "tidak":
            set_context(user_id,status="input_nop")
            return (
                "Baik, kita ulang dari awal.\n"
                "Silakan masukkan Nomor Pokok Wajib Pajak Daerah (NPWPD).\nKetik 'batal' untuk keluar."
            )

        return "Silakan ketik 'ya' atau 'tidak'.\nKetik 'batal' untuk keluar."

    # ❌ STATE TIDAK VALID
    reset_context(user_id)
    return "Terjadi kesalahan alur. Silakan ulangi dari awal.\n Ada yang bisa saya bantu lagi?"

def bayarPBB(status, context, user_id, q, messageMentah):
    # 🔹 TANYA JENIS PAJAK
    if status == "tanya_pajak":
        set_context(user_id, pajak="pbb", status="input_nop")
        return (
            "Silakan masukkan Nomor Objek Pajak (NOP).\n"
            "Ketik 'batal' untuk keluar."
        )

    # 🔹 INPUT NOP
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

    # 🔹 INPUT NIK
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

    # 🔹 INPUT TAHUN
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

    # 🔹 KONFIRMASI
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

    # ❌ STATE TIDAK VALID
    reset_context(user_id)
    return "Terjadi kesalahan alur. Silakan ulangi dari awal.\n Ada yang bisa saya bantu lagi?"

def chat(user_id: str, message: str) -> str:
    q = preprocess_user_input(message)
    messageMentah = message
    ctx = get_context(user_id)

    # 🔹 LOGGING HELPER
    # successful=True means the bot successfully handled/understood the request.
    # We only log when successful=False (i.e. we need training data).
    def reply(msg, intent="UNKNOWN", score=0.0, successful=True):
        if not successful:
            # Handle None intent
            safe_intent = intent if intent else "NONE"
            log_conversation(user_id, message, safe_intent, score, msg)
        return msg

    # GLOBAL CANCEL
    if ctx and (q == "batal" or messageMentah.strip().lower() == "batal"):
        reset_context(user_id)
        # Cancellation is a "successful" flow command, usually no need to train on it.
        return reply("Transaksi dibatalkan. Ada yang bisa saya bantu lagi?", "CANCEL", 1.0, successful=True)
    
    if ctx:
        status = ctx.get("status")
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
            ctx['pajak'] = pajak # Fix: Update local context immediately

        pajak = ctx.get("pajak")

        if pajak in PAJAK_KEYWORDS and pajak != "pbb":
            return reply(bayarNonPBB(status, pajak, ctx, user_id, q, messageMentah), f"FLOW_{pajak.upper()}", 1.0, successful=True)
        
        elif pajak == "pbb":
            return reply(bayarPBB(status, ctx, user_id, q, messageMentah), "FLOW_PBB", 1.0, successful=True)
        
    intent, answer, score = detect_faq(q)
    print(f"Intent: {intent}, Score: {score}")

    # Direct payment-flow trigger for transactional utterances (even when FAQ intent matched cara_bayar_*).
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
                intent, score, successful=False # Ambiguous initial request
            )

        pajak = pajaks[0]
        if pajak and pajak != "pbb":
            set_context(user_id,status="input_nop", pajak=pajak)
            return reply(
                "Silakan masukkan Nomor Pokok Wajib Pajak Daerah (NPWPD).\n"
                "Ketik 'batal' untuk keluar.",
                intent, score, successful=True
            )
        
        elif pajak == "pbb":
            set_context(user_id, status="input_nop", pajak=pajak)
            return reply(
                "Silakan masukkan Nomor Objek Pajak (NOP).\n"
                "Ketik 'batal' untuk keluar.",
                intent, score, successful=True
            )
        
        set_context(user_id, status="tanya_pajak")
        return reply("Baik, mau bayar pajak apa? (contoh: restoran, PBB, hotel)", intent, score, successful=True)
    elif not intent:
        return reply("Halo 👋 Ada yang bisa saya bantu terkait pajak?", "NO_INTENT", 0.0, successful=False)

    return reply(answer, intent, score, successful=True)



# TEST
if __name__ == "__main__":
    init()
    user_id = "test_user"
    reset_context(user_id) # Reset context on startup
    while True:
        q = input("Anda: ")
        if q.lower() in ["exit", "quit"]:
            break
        print("AI :", chat(user_id, q))
