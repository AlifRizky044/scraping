import re
try:
    import joblib
except Exception:  # pragma: no cover
    joblib = None

try:
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # pragma: no cover
    cosine_similarity = None

# ======================================================
# LOAD MODEL (OPTIONAL - JIKA PAKAI ML FAQ)
# ======================================================
try:
    if joblib is None or cosine_similarity is None:
        raise RuntimeError("Dependencies unavailable")
    vectorizer = joblib.load("models/vectorizer.pkl")
    faq_vectors = joblib.load("models/faq_vectors.pkl")
    faq_intents = joblib.load("models/faq_intents.pkl")
    answers = joblib.load("models/answers.pkl")
except Exception:
    vectorizer = faq_vectors = faq_intents = answers = None


# ======================================================
# KONFIGURASI
# ======================================================
PAJAK_KEYWORDS = [
    "hotel", "restoran", "hiburan",
    "reklame", "parkir", "air tanah", "pbb"
]


# ======================================================
# CONTEXT STORE (MULTI USER - IN MEMORY)
# ======================================================
USER_CONTEXTS = {}

def get_context(user_id):
    return USER_CONTEXTS.setdefault(user_id, {})

def set_context(user_id, **kwargs):
    ctx = get_context(user_id)
    ctx.update(kwargs)

def reset_context(user_id):
    USER_CONTEXTS.pop(user_id, None)


# ======================================================
# UTIL VALIDATOR
# ======================================================
def normalize(text: str) -> str:
    return text.lower().strip()

def extract_nop(text):
    m = re.search(r"\b\d{18}\b", text)
    return m.group() if m else None

def extract_npwpd(text):
    m = re.search(r"\b\d{16}\b", text)
    return m.group() if m else None

def extract_nik(text):
    m = re.search(r"\b\d{16}\b", text)
    return m.group() if m else None

def extract_nib(text):
    m = re.search(r"\b\d{13}\b", text)
    return m.group() if m else None


# ======================================================
# FAQ DETECTION (OPTIONAL)
# ======================================================
def detect_faq(question):
    if not vectorizer:
        return None, None, 0.0

    q_vec = vectorizer.transform([question])
    sim = cosine_similarity(q_vec, faq_vectors)

    idx = sim.argmax()
    score = sim.max()

    if score < 0.5:
        return None, None, score

    return faq_intents[idx], answers[idx], score


# ======================================================
# FSM NON PBB
# ======================================================
def bayar_non_pbb(user_id, q):
    ctx = get_context(user_id)
    status = ctx.get("status")

    # INPUT NPWPD
    if status == "input_nop":
        nop = extract_npwpd(q)
        if not nop:
            return (
                "NPWPD tidak valid.\n"
                "Silakan masukkan NPWPD yang benar.\n"
                "Ketik 'batal' untuk keluar."
            )

        set_context(user_id, status="input_id", nop=nop)
        return (
            f"NPWPD: {nop}\n"
            "Silakan masukkan NIK / NIB.\n"
            "Ketik 'batal' untuk keluar."
        )

    # INPUT NIK / NIB
    if status == "input_id":
        nik = extract_nik(q)
        nib = extract_nib(q)

        if not nik and not nib:
            return (
                "NIK / NIB tidak valid.\n"
                "Silakan masukkan kembali.\n"
                "Ketik 'batal' untuk keluar."
            )

        value = nik or nib
        label = "NIK" if len(value) == 16 else "NIB"

        set_context(
            user_id,
            status="konfirmasi",
            id_value=value,
            id_label=label
        )

        return (
            f"NPWPD: {ctx['nop']}\n"
            f"{label}: {value}\n"
            "Apakah data sudah benar?\n"
            "➡ ketik 'ya'\n"
            "➡ ketik 'tidak'\n"
            "➡ ketik 'batal'"
        )

    # KONFIRMASI
    if status == "konfirmasi":
        if q == "ya":
            reset_context(user_id)
            return (
                "Silakan lanjutkan pembayaran melalui link berikut:\n"
                "https://pajak.medan.go.id/bayar/nonpbb"
            )

        if q == "tidak":
            set_context(user_id, status="input_nop")
            return "Baik, silakan masukkan NPWPD kembali."

        return "Silakan ketik 'ya' atau 'tidak'."

    reset_context(user_id)
    return "Terjadi kesalahan alur. Silakan ulangi."


# ======================================================
# FSM PBB
# ======================================================
def bayar_pbb(user_id, q):
    ctx = get_context(user_id)
    status = ctx.get("status")

    # INPUT NOP
    if status == "input_nop":
        nop = extract_nop(q)
        if not nop:
            return (
                "NOP tidak valid.\n"
                "Silakan masukkan NOP yang benar.\n"
                "Ketik 'batal' untuk keluar."
            )

        set_context(user_id, status="input_nik", nop=nop)
        return f"NOP: {nop}\nSilakan masukkan NIK."

    # INPUT NIK
    if status == "input_nik":
        nik = extract_nik(q)
        if not nik:
            return "NIK tidak valid. Silakan masukkan kembali."

        set_context(user_id, status="konfirmasi", nik=nik)

        if len(nik) == 16:
            return (
                f"NPWPD: {ctx['nop']}\n"
                f"NIK: {nik}\n"
                "Apakah data sudah benar?\n"
                "➡ ketik 'ya'\n"
                "➡ ketik 'tidak'\n"
                "➡ ketik 'batal'"
            )
        else:
            return (
                f"NPWPD: {ctx['nop']}\n"
                f"NIB: {nik}\n"
                "Apakah data sudah benar?\n"
                "➡ ketik 'ya'\n"
                "➡ ketik 'tidak'\n"
                "➡ ketik 'batal'"
            )

    # KONFIRMASI
    if status == "konfirmasi":
        if q == "ya":
            reset_context(user_id)
            return (
                "Silakan lanjutkan pembayaran melalui link berikut:\n"
                "https://pajak.medan.go.id/bayar/pbb"
            )

        if q == "tidak":
            set_context(user_id, status="input_nop")
            return "Baik, silakan masukkan NOP kembali."

        return "Silakan ketik 'ya' atau 'tidak'."

    reset_context(user_id)
    return "Terjadi kesalahan."


# ======================================================
# CHAT HANDLER (ENTRY POINT)
# ======================================================
def chat(user_id: str, message: str) -> str:
    q = normalize(message)
    messageMentah = message
    ctx = get_context(user_id)

    # GLOBAL CANCEL
    if ctx and q == "batal":
        reset_context(user_id)
        return "Transaksi dibatalkan. Ada yang bisa saya bantu lagi?"

    # CONTEXT FLOW
    if ctx:
        pajak = ctx.get("pajak")
        if pajak == "pbb":
            return bayar_pbb(user_id, q, messageMentah)
        return bayar_non_pbb(user_id, q)

    # INTENT: BAYAR PAJAK
    if "pbb" in q:
        set_context(user_id, pajak="pbb", status="input_nop")
        return (
            "Baik, pembayaran PBB.\n"
            "Silakan masukkan Nomor Objek Pajak (NOP).\n"
            "Ketik 'batal' untuk keluar."
        )

    if any(p in q for p in PAJAK_KEYWORDS if p != "pbb"):
        set_context(user_id, pajak="nonpbb", status="input_nop")
        return (
            "Baik, pembayaran pajak daerah.\n"
            "Silakan masukkan Nomor Pokok Wajib Pajak Daerah (NPWPD).\n"
            "Ketik 'batal' untuk keluar."
        )

    # FAQ
    intent, answer, score = detect_faq(q)
    if intent:
        return answer

    return "Halo 👋 Ada yang bisa saya bantu terkait pajak?"


# ======================================================
# CLI TEST (LOCAL)
# ======================================================
if __name__ == "__main__":
    print("=== CHATBOT PAJAK (PRODUCTION READY) ===")
    user_id = "test_user"

    while True:
        msg = input("Anda: ")
        if msg.lower() in ("exit", "quit"):
            break
        print("Bot :", chat(user_id, msg))
