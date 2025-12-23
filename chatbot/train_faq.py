import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from pathlib import Path

DATA_PATH = "data/faq_fixed.csv"
MODEL_DIR = Path("models")

# pastikan folder models ada
MODEL_DIR.mkdir(exist_ok=True)

# load dataset
df = pd.read_csv(DATA_PATH)

# validasi kolom
required_cols = {"intent", "question", "answer"}
if not required_cols.issubset(df.columns):
    raise ValueError("CSV wajib punya kolom: intent, question, answer")

# vectorizer
vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    max_features=8000,
    sublinear_tf=True,
    stop_words=None
)

# training vector
faq_vectors = vectorizer.fit_transform(df["question"].astype(str))

# simpan semua yang dibutuhkan runtime
joblib.dump(vectorizer, MODEL_DIR / "vectorizer.pkl")
joblib.dump(faq_vectors, MODEL_DIR / "faq_vectors.pkl")
joblib.dump(df["intent"].tolist(), MODEL_DIR / "faq_intents.pkl")
joblib.dump(df["answer"].tolist(), MODEL_DIR / "answers.pkl")

print("✅ FAQ similarity model trained & saved")
