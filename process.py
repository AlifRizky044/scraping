import math
import json
from collections import Counter
from typing import List, Dict
from constant import *
import random

# Dokumen contoh
documents = [
    "Rubah coklat cepat melompati anjing malas.",
    "Jangan pernah melompati anjing malas dengan cepat.",
    "Rubah coklat cerah melompat dengan cepat."
]

with open('data.json', 'r') as file:
    # Step 3: Load the JSON data
    data = json.load(file)

documents = []

nama = []

skills = []

pendidikan = []

experience = []

def getPendidikanTerakhir(list_edu):
    res = 0
    for text in list_edu:
        for word in pendidikan_list:
            if word.lower() in text.lower():
                for index, item in enumerate(level_pendidikan_list):
                    if (word.lower() in item["title"] and item["level"] > res):
                        res = item["level"]
                        break
                break
    return res

for d in data:
    nama.append(d["Name"])

    if isinstance(d["Skills"], list):
        skills.append(" ".join(d["Skills"]))
    else:
        skills.append(d["Skills"])

    if isinstance(d["Experience"], list):
        experience.append(" ".join(d["Experience"]))
    else:
        experience.append(d["Experience"])

    if(len(d["Pendidikan"]) > 0):
        res = getPendidikanTerakhir(d["Pendidikan"])
        pendidikan.append(res)
    else:
        pendidikan.append(0)



print(len(nama))
print(len(pendidikan))

def preprocess(text: str) -> List[str]:
    """Membagi dan memproses teks menjadi token."""
    return text.lower().split()

def compute_tf(doc: List[str]) -> Dict[str, float]:
    """Menghitung frekuensi term (TF) untuk sebuah dokumen."""
    tf = Counter(doc)
    doc_length = len(doc)
    return {term: freq / doc_length for term, freq in tf.items()}

def compute_idf(documents: List[List[str]]) -> Dict[str, float]:
    """Menghitung inverse document frequency (IDF) untuk seluruh korpus."""
    num_docs = len(documents)
    idf = {}
    all_terms = set(term for doc in documents for term in doc)
    
    for term in all_terms:
        containing_docs = sum(1 for doc in documents if term in doc)
        idf[term] = math.log(num_docs / (1 + containing_docs))
    
    return idf

def compute_tfidf(doc: List[str], idf: Dict[str, float]) -> Dict[str, float]:
    """Menghitung TF-IDF untuk sebuah dokumen."""
    tf = compute_tf(doc)
    return {term: tf_val * idf[term] for term, tf_val in tf.items()}

def normalize_vector(tfidf: Dict[str, float]) -> Dict[str, float]:
    """Menormalkan vektor TF-IDF menggunakan normalisasi Euclidean (L2)."""
    norm = math.sqrt(sum(score ** 2 for score in tfidf.values()))
    return {term: score / norm for term, score in tfidf.items()}

# Mengonversi dokumen TF-IDF yang dinormalisasi ke dalam format vektor
def tfidf_to_vector(tfidf: Dict[str, float], terms: List[str]) -> List[float]:
    return [tfidf.get(term, 0.0) for term in terms]

# Memproses dokumen
preprocessed_skills = [preprocess(doc) for doc in skills]

# Menghitung IDF untuk seluruh korpus
idf_skills = compute_idf(preprocessed_skills)

# Menghitung dan menormalkan TF-IDF untuk setiap dokumen
tfidf_skills = [normalize_vector(compute_tfidf(doc, idf_skills)) for doc in preprocessed_skills]

terms_skills = list(idf_skills.keys())
vectors_skills = [tfidf_to_vector(tfidf, terms_skills) for tfidf in tfidf_skills]

# Memproses dokumen
preprocessed_exp = [preprocess(doc) for doc in experience]

# Menghitung IDF untuk seluruh korpus
idf_exp = compute_idf(preprocessed_exp)

# Menghitung dan menormalkan TF-IDF untuk setiap dokumen
tfidf_exp = [normalize_vector(compute_tfidf(doc, idf_exp)) for doc in preprocessed_exp]

terms_exp = list(idf_exp.keys())
vectors_exp = [tfidf_to_vector(tfidf, terms_exp) for tfidf in tfidf_exp]

# Fungsi untuk menginisialisasi centroid secara acak
def inisialisasi_centroid(data, k, seed):
    if seed is not None:
        random.seed(seed)
    return random.sample(data, k)

# Fungsi untuk menghitung jarak Euclidean antara dua titik
def jarak_euclidean(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

# Fungsi untuk menetapkan titik data ke centroid terdekat
def tetapkan_cluster(data, centroid):
    cluster = {}
    owner = {}
    for idx, titik in enumerate(data):
        jarak = [jarak_euclidean(titik, c) for c in centroid]
        jarak_min = min(jarak)
        kluster = jarak.index(jarak_min)
        if kluster in cluster:
            owner[kluster].append(nama[idx])
            cluster[kluster].append(titik)
        else:
            owner[kluster] = [nama[idx]]
            cluster[kluster] = [titik]
    return owner, cluster

# Fungsi untuk memperbarui centroid berdasarkan rata-rata titik dalam setiap kluster
def perbarui_centroid(cluster):
    centroid_baru = []
    for kluster in cluster.values():
        centroid_baru.append([sum(dim) / len(dim) for dim in zip(*kluster)])
    return centroid_baru

# Fungsi utama untuk menjalankan algoritma k-means
def kmeans(data, k, iterasi_maks=100, seed=None):
    centroid = inisialisasi_centroid(data, k, seed)
    owner = {}
    for _ in range(iterasi_maks):
        owner, cluster = tetapkan_cluster(data, centroid)
        centroid_baru = perbarui_centroid(cluster)
        if centroid_baru == centroid:
            break
        centroid = centroid_baru
    return cluster, centroid, owner

# Fungsi untuk menghitung kesamaan kosinus antara dua vektor
def cosine_similarity(vec1, vec2):
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a ** 2 for a in vec1))
    magnitude2 = math.sqrt(sum(b ** 2 for b in vec2))
    if not magnitude1 or not magnitude2:
        return 0
    return dot_product / (magnitude1 * magnitude2)


# Convert data to feature vectors
feature_vectors = []
for index, item in enumerate(nama):
    features = [pendidikan[index]] + vectors_skills[index] + vectors_exp[index]
    feature_vectors.append(features)

# Apply k-means clustering
k = 2
seed = len(nama)/2
clusters, centroids, owner = kmeans(feature_vectors, k, seed=seed)

# print("Feature Vectors:", feature_vectors)
# print("Clusters:", clusters)
# print("Centroids:", centroids)


# Menghitung dan menampilkan kesamaan kosinus

print("\nKesamaan Kosinus:")
for kluster, titik_data in clusters.items():
    for idx, titik in enumerate(titik_data):
        cos_sim = cosine_similarity(titik, centroids[0])
        print(f"Kesamaan Kosinus untuk Index {idx} dalam cluster {kluster}: {cos_sim:.4f}")






print(owner)
