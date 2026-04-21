import csv
import re
from collections import defaultdict
from pathlib import Path


SOURCE_CSV = Path("data/faq_fixed.csv")
OUTPUT_CSV = Path("data/chatty_15_per_context.csv")
TARGET_PER_INTENT = 15
INTENT_EXCLUDE_PATTERNS = {
    "kontak_resmi": [r"pengaduan"],
}


SLANG_REPLACEMENTS = {
    r"\bbagaimana\b": "gimana",
    r"\bdimana\b": "dmn",
    r"\bapakah\b": "apa",
    r"\bberapa\b": "brp",
    r"\bpajak\b": "pajak",
    r"\bnomor\b": "nomor",
    r"\bkontak\b": "kontak",
    r"\bjatuh tempo\b": "deadline",
    r"\bwajib\b": "wajib",
    r"\bpelayanan\b": "layanan",
}

CHAT_OPENERS = [
    "",
    "min ",
    "bang ",
    "kak ",
    "permisi ",
]

CHAT_CLOSERS = [
    "",
    " ya",
    " dong",
    " nih",
]


def normalize_space(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_punctuation(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return normalize_space(text)


def slangify(text: str) -> str:
    result = text.lower()
    for pattern, replacement in SLANG_REPLACEMENTS.items():
        result = re.sub(pattern, replacement, result)
    return normalize_space(result)


def chatify_question(question: str, style_idx: int) -> str:
    base = strip_punctuation(question)
    slang = slangify(base)
    base = re.sub(r"^(min|bang|kak|permisi)\s+", "", base)
    slang = re.sub(r"^(min|bang|kak|permisi)\s+", "", slang)

    cores = [
        base,
        slang,
        f"{slang} dong",
        f"{slang} ya",
    ]
    core = normalize_space(cores[style_idx % len(cores)])

    opener = CHAT_OPENERS[style_idx % len(CHAT_OPENERS)]
    closer = CHAT_CLOSERS[(style_idx // len(CHAT_OPENERS)) % len(CHAT_CLOSERS)]
    if re.search(r"\b(ya|dong|nih|plis)$", core):
        closer = ""

    # Hindari pengulangan kata tanya yang aneh seperti "gimana bagaimana ..."
    core = re.sub(r"\bgimana bagaimana\b", "gimana", core)
    core = re.sub(r"\bgimana apa\b", "apa", core)
    core = re.sub(r"\bapa apa\b", "apa", core)
    core = re.sub(r"\bdmn dimana\b", "dmn", core)
    text = normalize_space(f"{opener}{core}{closer}")
    text = re.sub(r"\b(ya|dong|nih|plis)\s+\1\b", r"\1", text)
    text = re.sub(r"\b(ya|dong|nih|plis)\s+(ya|dong|nih|plis)$", r"\1", text)
    return normalize_space(text)


def load_questions_by_intent(path: Path):
    grouped = defaultdict(list)
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            intent = (row.get("intent") or "").strip()
            question = (row.get("question") or "").strip()
            if intent and question:
                grouped[intent].append(question)
    return grouped


def main():
    questions_by_intent = load_questions_by_intent(SOURCE_CSV)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["intent", "question"])

        for intent in sorted(questions_by_intent.keys()):
            seen = set()
            selected = []
            source_questions = questions_by_intent[intent]
            excluded = INTENT_EXCLUDE_PATTERNS.get(intent, [])
            if excluded:
                filtered = []
                for q in source_questions:
                    ql = q.lower()
                    if any(re.search(p, ql) for p in excluded):
                        continue
                    filtered.append(q)
                if filtered:
                    source_questions = filtered
            style_idx = 0
            q_idx = 0

            # Putar semua seed question agar variasi tidak menumpuk di 1 pertanyaan.
            while len(selected) < TARGET_PER_INTENT:
                base_q = source_questions[q_idx % len(source_questions)]
                candidate = chatify_question(base_q, style_idx)
                key = candidate.lower()
                if key not in seen and len(candidate.split()) >= 2:
                    seen.add(key)
                    selected.append(candidate)
                style_idx += 1
                q_idx += 1

                # fallback sangat jarang, kalau terlalu banyak duplikat.
                if style_idx > 600 and len(selected) < TARGET_PER_INTENT:
                    fallback = normalize_space(f"min {slangify(strip_punctuation(base_q))} dong")
                    if fallback.lower() not in seen:
                        seen.add(fallback.lower())
                        selected.append(fallback)

            for q in selected:
                writer.writerow([intent, q])

    total_intents = len(questions_by_intent)
    total_rows = total_intents * TARGET_PER_INTENT
    print(f"Generated {total_rows} rows ({TARGET_PER_INTENT} per intent) at {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
