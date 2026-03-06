import re
import csv
from pathlib import Path
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from rapidfuzz import process, fuzz

factory = StemmerFactory()
stemmer = factory.create_stemmer()



SLANG_DICT = {
    # umum
    "apa": "apa",
    "ap": "apa",
    "apakah": "apa",
    "akah": "apa",
    "itu": "itu",
    "it": "itu",
    "tu": "itu",
    "y": "yang",
    "yg": "yang",
    "gmna": "bagaimana",
    "gmn": "bagaimana",
    "bgmn": "bagaimana",
    "gimana": "bagaimana",
    "brp": "berapa",
    "brrp": "berapa",
    "kpn": "kapan",
    "kpan": "kapan",
    "dmn": "dimana",
    "dman": "dimana",
    "mana": "dimana",
    "knp": "kenapa",
    "pjk": "pajak",
    "mdn": "medan",
    "npwpd": "npwpd",
    "nop": "npwpd",
    "pjl": "pajak reklame",
    "bpd": "bapenda",
    "bapeda": "bapenda",     # sering salah
    "bapenda": "bapenda",
    "dispenda": "bapenda",
    "bpprd": "bapenda",
    "medan": "medan",
    "mdn": "medan",
    "pajk": "pajak",
    "byr": "bayar",
    "bry": "bayar",
    "byar": "bayar",
    "bayr": "bayar",
    "jth": "jatuh",
    "tempo": "tempo",
    "dnda": "denda",
    "pbb": "pbb",
    "bbp": "pbb",
    "onlen": "online",
    "oln": "online",
    "rst": "restoran",
    "rm": "restoran",
    "htl": "hotel",
    "hib": "hiburan",
    "prkr": "parkir",
    "parkiran": "parkir",
    "wpd": "wajib pajak",
    "wjb": "wajib",
    
    # english / loanwords / common casual
    "deadline": "jatuh tempo",
    "share": "bagikan",
    "loc": "lokasi",
    "location": "lokasi",
    "call": "panggilan",
    "center": "pusat",
    "cek": "periksa",
    "cekin": "periksa",
    "liat": "lihat",
    "tau": "tahu",
    "kasih": "beri",
    "jelasin": "jelaskan",
    "sebutin": "sebutkan",
    "ngurusin": "mengurus",
    "ngurusi": "mengurus",
    "trus": "terus",
    "trs": "terus",
    "dtg": "datang",
    "sy": "saya",
    "ak": "saya",
    "aku": "saya",
    "gak": "tidak",
    "gk": "tidak",
    "ga": "tidak",
    "nggak": "tidak",
    "enggak": "tidak",
    "bkn": "bukan",
    "pke": "pakai",
    "pake": "pakai",
    "sdh": "sudah",
    "udh": "sudah",
    "blm": "belum",
    "lmbt": "lambat",
    "tlmbat": "lambat",
    "telat": "lambat",
    "tgl": "tanggal",
    "thn": "tahun",
    "bln": "bulan",

    # religius / musiman
    "ramadan": "ramadhan",
    "romadon": "ramadhan",
    "romadhon": "ramadhan",
    "puasa": "ramadhan",
    "bukber": "buka bersama",
    "sahur": "ramadhan",

    # percakapan umum tambahan
    "pls": "tolong",
    "plis": "tolong",
    "tolongin": "tolong",
    "dong": "tolong",
    "min": "admin",
    "adminnya": "admin",
    "cs": "kontak",
    "nomer": "nomor",
    "tlp": "telepon",
    "telp": "telepon",
    "wa": "whatsapp",
    "wha": "whatsapp",
    "kontek": "kontak",
    "inpo": "info",
    "infoin": "info",
    "bgt": "banget",
    "bangettt": "banget",
    "bgtu": "begitu",
    "sm": "sama",
    "sma": "sama",
    "dr": "dari",
    "keq": "kayak",
    "kyk": "kayak",
    "krn": "karena",
    "krna": "karena",
    "udahh": "sudah",
    "udhh": "sudah",
    "belom": "belum",
    "blom": "belum",
    "gimanaa": "bagaimana",
    "gmnnya": "bagaimana",
    "dimn": "dimana",
    "dmnya": "dimana",
}

KAMUS_KATA = [
]
KAMUS_SET = set()
AUTO_SLANG_DICT = {}
NORMALIZATION_MAP = {}

ISTILAH_RESMI = {
    "npwpd", "sptpd", "skpd", "skpdkb", "wajib pajak"
}

def _generate_auto_aliases(word: str):
    aliases = set()
    if len(word) < 4:
        return aliases

    # Pola umum singkatan chat: hapus vokal di tengah kata.
    mid_no_vowel = word[0] + re.sub(r"[aiueo]", "", word[1:])
    if len(mid_no_vowel) >= 3 and mid_no_vowel != word:
        aliases.add(mid_no_vowel)

    # Hapus vokal penuh untuk kata panjang tertentu.
    all_no_vowel = re.sub(r"[aiueo]", "", word)
    if len(all_no_vowel) >= 3 and all_no_vowel != word:
        aliases.add(all_no_vowel)

    # Ringkas huruf berulang (mis. "bangettt" -> "banget").
    collapsed = re.sub(r"(.)\1+", r"\1", word)
    if len(collapsed) >= 3 and collapsed != word:
        aliases.add(collapsed)

    return aliases

def init():
    if KAMUS_KATA:
        return
    NORMALIZATION_MAP.update(SLANG_DICT)
    # Kamus typo dipakai untuk kata baku/canonical (bukan alias slang), agar koreksi tidak bias.
    canonical_terms = set(NORMALIZATION_MAP.values())
    # Tambahkan kosakata dari dataset FAQ agar typo kata biasa ikut bisa diperbaiki.
    faq_path = Path(__file__).resolve().parent / "data" / "faq_fixed.csv"
    faq_terms = set()
    if faq_path.exists():
        with faq_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                q = str(row.get("question", "")).lower()
                a = str(row.get("answer", "")).lower()
                for text in (q, a):
                    cleaned = re.sub(r"[^a-zA-Z\s]", " ", text)
                    for token in cleaned.split():
                        if len(token) > 2:
                            canonical_terms.add(token)
                            faq_terms.add(token)

    # Auto-generate singkatan/alias untuk token FAQ agar cakupan slang lebih luas.
    alias_targets = {}
    for token in faq_terms:
        for alias in _generate_auto_aliases(token):
            if alias in NORMALIZATION_MAP:
                continue
            alias_targets.setdefault(alias, set()).add(token)

    for alias, targets in alias_targets.items():
        # Hanya pakai alias yang mengarah ke 1 kata agar tidak ambigu.
        if len(targets) == 1:
            target = next(iter(targets))
            AUTO_SLANG_DICT[alias] = target

    NORMALIZATION_MAP.update(AUTO_SLANG_DICT)
    for _, v in NORMALIZATION_MAP.items():
        if len(v) > 2:
            canonical_terms.add(v)

    KAMUS_KATA.extend(sorted(canonical_terms))
    KAMUS_SET.update(KAMUS_KATA)

def correct_typo(word):
    if word in ISTILAH_RESMI:
        return word
    if len(word) <= 2:
        return word
    # Jika token berupa singkatan tanpa vokal dan tidak ada di map, jangan dipaksa jadi kata lain.
    if not re.search(r"[aiueo]", word) and word not in NORMALIZATION_MAP:
        return word
    if word in KAMUS_SET:
        return word

    # Dynamic threshold: kata pendek sering typo 1 huruf.
    if len(word) <= 4:
        cutoff = 60
    elif len(word) <= 7:
        cutoff = 75
    else:
        cutoff = 82

    match = process.extractOne(word, KAMUS_KATA, scorer=fuzz.ratio, score_cutoff=cutoff)
    if not match:
        return word

    candidate, score, _ = match
    # Guard agar tidak terlalu agresif mengganti kata yang jauh.
    if abs(len(candidate) - len(word)) > 2:
        return word
    if word[0] != candidate[0] and score < 90:
        return word
    return candidate


def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s?]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def expand_singkatan(words):
    result = []
    for w in words:
        if w in NORMALIZATION_MAP:
            result.extend(NORMALIZATION_MAP[w].split())
        else:
            result.append(w)
    return result


def preprocess_id(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    tokens = text.split()
    stemmed = [stemmer.stem(t) for t in tokens]
    return " ".join(stemmed)

def preprocess_user_input(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    # stemming
    tokens = text.split()
    stemmed = [stemmer.stem(t) for t in tokens]

    words = expand_singkatan(stemmed)

    # 3️⃣ typo correction
    words = [correct_typo(w) for w in words]

    # 4️⃣ singkatan level 2
    words = expand_singkatan(words)

    return " ".join(words)
