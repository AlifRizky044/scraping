import re
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
}

KAMUS_KATA = [
]

ISTILAH_RESMI = {
    "npwpd", "sptpd", "skpd", "skpdkb", "wajib pajak"
}

def init():
    # Only add values (standard words) and keys longer than 2 chars to avoid bad fuzzy matches (e.g. 'ak')
    terms = set(SLANG_DICT.values())
    for k in SLANG_DICT.keys():
        if len(k) > 2:
            terms.add(k)
    KAMUS_KATA.extend(list(terms))

def correct_typo(word):
    if word in ISTILAH_RESMI:
        return word

    match = process.extractOne(word, KAMUS_KATA, scorer=fuzz.ratio, score_cutoff=85)
    return match[0] if match else word


def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s?]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def expand_singkatan(words):
    result = []
    for w in words:
        if w in SLANG_DICT:
            result.extend(SLANG_DICT[w].split())
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

