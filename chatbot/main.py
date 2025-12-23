import joblib
import re
from sklearn.metrics.pairwise import cosine_similarity

# LOAD MODELS
vectorizer = joblib.load("models/vectorizer.pkl")
faq_vectors = joblib.load("models/faq_vectors.pkl")
faq_intents = joblib.load("models/faq_intents.pkl")
answers = joblib.load("models/answers.pkl")

PAJAK_KEYWORDS = [
    "hotel", "restoran", "hiburan", "reklame", "penerangan jalan",
    "parkir", "air tanah", "mineral bukan logam", "walet", "pbb", "bphtb"
]

# 🔹 STATE RINGAN (SINGLE USER)
waiting_pajak = False
context = {}

def get_nop(text):
    match = re.search(r"\b\d{18}\b", text)
    return match.group() if match else None

def get_nik(text):
    match = re.search(r"\b\d{16}\b", text)
    return match.group() if match else None

def reset_context():
    context.clear()

def set_context(**kwargs):
    for k, v in kwargs.items():
        context[k] = v
def detect_pajak(text):
    text = text.lower()
    for p in PAJAK_KEYWORDS:
        if p in text:
            return p
    return None


def detect_faq(question):
    q_vec = vectorizer.transform([question])
    sim = cosine_similarity(q_vec, faq_vectors)

    idx = sim.argmax()
    score = sim.max()

    if score < 0.5:
        return None, None, score

    return faq_intents[idx], answers[idx], score


def chat(question: str) -> str:
    q = question.lower().strip()

    # 🔴 GLOBAL CANCEL
    if context and "batal" in q:
        reset_context()
        return "Ok, pembayaran pajak dibatalkan. Ada yang bisa saya bantu lagi?"

    # ======================================================
    # 🟡 CONTEXT FLOW (FSM)
    # ======================================================
    if context:
        status = context.get("status")

        # 🔹 TANYA JENIS PAJAK
        if status == "tanya_pajak":
            pajak = detect_pajak(q)

            if not pajak:
                return (
                    "Maaf, jenis pajak tidak dikenali.\n"
                    "Silakan sebutkan jenis pajak atau ketik 'batal'."
                )

            if pajak != "pbb":
                reset_context()
                return (
                    f"Baik, untuk pembayaran pajak {pajak.upper()} "
                    f"silakan lanjutkan melalui link berikut:\n"
                    f"https://pajak.medan.go.id/bayar/{pajak.replace(' ', '-')}"
                )

            set_context(pajak="pbb", status="input_nop")
            return (
                "Silakan masukkan Nomor Objek Pajak (NOP).\n"
                "Ketik 'batal' untuk keluar."
            )

        # 🔹 INPUT NOP
        if status == "input_nop":
            nop = get_nop(q)
            if not nop:
                return (
                    "NOP tidak valid.\n"
                    "Silakan masukkan NOP yang benar.\n"
                    "Ketik 'batal' untuk keluar."
                )

            set_context(status="input_nik", nop=nop)
            return (
                f"NOP Anda: {nop}\n"
                "Silakan masukkan NIK.\n"
                "Ketik 'batal' untuk keluar."
            )

        # 🔹 INPUT NIK
        if status == "input_nik":
            nik = get_nik(q)
            if not nik:
                return (
                    "NIK tidak valid.\n"
                    "Silakan masukkan NIK yang benar.\n"
                    "Ketik 'batal' untuk keluar."
                )

            set_context(status="konfirmasi", nik=nik)
            return (
                f"NOP: {context.get('nop')}\n"
                f"NIK: {nik}\n"
                "Apakah data sudah benar?\n"
                "➡ ketik 'ya' untuk lanjut\n"
                "➡ ketik 'tidak' untuk ulang\n"
                "➡ ketik 'batal' untuk keluar"
            )

        # 🔹 KONFIRMASI
        if status == "konfirmasi":
            if q == "ya":
                set_context(status="bayar_pajak")
                return (
                    "Silakan lanjutkan pembayaran melalui link berikut:\n"
                    "https://pajak.medan.go.id/bayar/pbb"
                )

            if q == "tidak":
                reset_context()
                set_context(status="input_nop")
                return (
                    "Baik, kita ulang dari awal.\n"
                    "Silakan masukkan Nomor Objek Pajak (NOP).\nKetik 'batal' untuk keluar."
                )

            return "Silakan ketik 'ya' atau 'tidak'.\nKetik 'batal' untuk keluar."

        # ❌ STATE TIDAK VALID
        reset_context()
        return "Terjadi kesalahan alur. Silakan ulangi dari awal.\n Ada yang bisa saya bantu lagi?"

    # ======================================================
    # 🟢 INTENT & FAQ (NO CONTEXT)
    # ======================================================
    intent, answer, score = detect_faq(q)
    print(f"Intent: {intent}, Score: {score}")

    if not intent:
        return "Maaf, saya belum memahami pertanyaan Anda."

    if intent == "bayar_pajak":
        pajak = detect_pajak(q)

        if pajak and pajak != "pbb":
            return (
                f"Baik, untuk pembayaran pajak {pajak.upper()} "
                f"silakan lanjutkan melalui link berikut:\n"
                f"https://pajak.medan.go.id/bayar/{pajak.replace(' ', '-')}"
            )
        
        elif pajak == "pbb":
            set_context(status="input_nop")
            return (
                "Silakan masukkan Nomor Objek Pajak (NOP).\n"
                "Ketik 'batal' untuk keluar."
            )
        
        set_context(status="tanya_pajak")
        return "Baik, mau bayar pajak apa? (contoh: restoran, PBB, hotel)"

    return answer



# TEST
if __name__ == "__main__":
    while True:
        q = input("Anda: ")
        if q.lower() in ["exit", "quit"]:
            break
        print("AI :", chat(q))
