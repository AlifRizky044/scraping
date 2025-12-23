import pandas as pd
import joblib
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# =========================
# LOAD DATASET
# =========================
df = pd.read_csv("data/faq_fixed.csv")

df["question"] = df["question"].str.lower().str.strip()
df["intent"] = df["intent"].str.lower().str.strip()

# =========================
# PIPELINE INTENT MODEL
# =========================
intent_model = Pipeline([
    ("tfidf", TfidfVectorizer(
        ngram_range=(1,3),
        min_df=2,
        max_df=0.9,
        sublinear_tf=True,
        max_features=10000
    )),
    ("clf", LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        solver="lbfgs"      # ✅ FIX MULTICLASS
    ))
])

# =========================
# TRAINING
# =========================
intent_model.fit(df["question"], df["intent"])

# =========================
# SAVE MODEL
# =========================
joblib.dump(intent_model, "models/intent.pkl")

print("✅ Intent model trained (MULTICLASS OK)")
