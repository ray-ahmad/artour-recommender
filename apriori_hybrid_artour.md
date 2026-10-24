---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.19.4
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

+++ {"id": "KLrUFG9tzfRG"}

# Library/Package Requirements

```{code-cell} ipython3
---
colab:
  base_uri: https://localhost:8080/
id: eEcfWxM22aiM
outputId: d3387610-5373-4d5b-f05e-ae8d8e74813b
---
# %pip install pandas numpy scikit-learn mlxtend tqdm Sastrawi requests
```

+++ {"id": "niHI_J4Nzjko"}

# Import

```{code-cell} ipython3
---
colab:
  base_uri: https://localhost:8080/
id: MS0xp6arzlBW
outputId: ddc5054a-8e77-46e2-a9be-99711c7e9c49
---
import pandas as pd
import numpy as np
import re
import os
import requests
from getpass import getpass
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
import warnings
import logging

warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger("jupyter_client").setLevel(logging.ERROR)
```

+++ {"id": "WFe-n0J1lnHe"}

# Config

```{code-cell} ipython3
:id: FgPdnk9RlmmD

REFRESH_TRIGGER_TOKEN_HEADER = "X-ARTOUR-REFRESH-TRIGGER-TOKEN"


def _get_refresh_trigger_token():
    # input token
    # token = getpass(f"Masukkan {REFRESH_TRIGGER_TOKEN_HEADER}: ")
    token = 'e9797abb-f7b0-497d-800b-7969597e5da6'
    return token


CONFIG = {
    "API": {
        "places": "https://api.artour-lampung.com/places",
        "interactions": "https://api.artour-lampung.com/user-interactions",
        "headers": {REFRESH_TRIGGER_TOKEN_HEADER: _get_refresh_trigger_token()}
    },
    "PREPROCESSING": {
        "min_rating_positive": 4.0
    },
    "APRIORI": {
        "min_absolute_support": 3,
        "k_max": 3
    },
    "MCRS": {
        "min_rating_scale": 1.0,
        "max_rating_scale": 5.0,
        "weight_cost": 0.5,
        "weight_benefit": 0.5
    }
}


def _fetch_json(url, headers, timeout=30):
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    body = response.json()
    return body["data"] if isinstance(body, dict) and "data" in body else body


def fetch_places_df(url, headers):
    """Ambil dataset places dari API lalu petakan ke skema kolom lama (placeId, placeName, dst)."""
    df = pd.json_normalize(_fetch_json(url, headers))

    if "status" in df.columns:
        df = df[df["status"] == "PUBLISHED"].copy()

    rename_map = {
        "id": "placeId",
        "name": "placeName",
        "description": "placeDescription",
        "address": "placeAddress",
        "categoryId": "placeCategoryId",
        "category.name": "placeCategoryName",
        "price": "placePrice",
        "rating": "placeRating",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Endpoint /places gak nyertain hashtags per item, jadi diisi kosong saja.
    if "placeHashtags" not in df.columns:
        df["placeHashtags"] = ""

    return df.reset_index(drop=True)


def fetch_interactions_df(url, headers):
    """Ambil dataset user-interactions dari API. Skema kolomnya sudah sama persis dengan CSV lama."""
    return pd.DataFrame(_fetch_json(url, headers))
```

# Exploratory Data Analysis

```{code-cell} ipython3
from IPython.display import display
import matplotlib.pyplot as plt


def gini_coefficient(values):
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return 0.0
    if np.all(arr == 0):
        return 0.0
    arr = np.sort(arr)
    n = arr.size
    cumulative = np.cumsum(arr)
    return float((n + 1 - 2 * np.sum(cumulative) / cumulative[-1]) / n)


print("[EDA] Mengambil dataset mentah dari API...")
raw_places = fetch_places_df(CONFIG["API"]["places"], CONFIG["API"]["headers"])
raw_interactions = fetch_interactions_df(CONFIG["API"]["interactions"], CONFIG["API"]["headers"])

print("[EDA] Ringkasan umum dataset")
eda_summary = pd.DataFrame([
    {"dataset": "places", "rows": len(raw_places), "columns": raw_places.shape[1], "duplicates": int(raw_places.duplicated().sum())},
    {"dataset": "interactions", "rows": len(raw_interactions), "columns": raw_interactions.shape[1], "duplicates": int(raw_interactions.duplicated().sum())},
])
display(eda_summary)

print("[EDA] Missing values per dataset")
place_missing = raw_places.isna().sum().sort_values(ascending=False)
interaction_missing = raw_interactions.isna().sum().sort_values(ascending=False)
display(pd.DataFrame({
    "places_missing": place_missing,
    "interactions_missing": interaction_missing,
}).fillna(0).astype(int).query("places_missing > 0 or interactions_missing > 0"))

print("[EDA] Statistik user dan item")
user_interaction_counts = raw_interactions.groupby("userId").size().sort_values(ascending=False)
item_interaction_counts = raw_interactions.groupby("refId").size().sort_values(ascending=False)
user_item_matrix = pd.crosstab(raw_interactions["userId"], raw_interactions["refId"])
non_zero = int((user_item_matrix > 0).sum().sum())
total_cells = int(user_item_matrix.shape[0] * user_item_matrix.shape[1])
density = (non_zero / total_cells) if total_cells > 0 else 0.0
sparsity = 1.0 - density

eda_metrics = pd.DataFrame([
    {"metric": "unique_users", "value": int(user_interaction_counts.shape[0])},
    {"metric": "unique_items", "value": int(item_interaction_counts.shape[0])},
    {"metric": "total_interactions", "value": int(len(raw_interactions))},
    {"metric": "matrix_density", "value": round(density, 6)},
    {"metric": "matrix_sparsity", "value": round(sparsity, 6)},
    {"metric": "gini_user_activity", "value": round(gini_coefficient(user_interaction_counts.values), 6)},
    {"metric": "gini_item_popularity", "value": round(gini_coefficient(item_interaction_counts.values), 6)},
])
display(eda_metrics)

print("[EDA] Cold-start profile berdasarkan threshold minimum interaksi user")
threshold_rows = []
for threshold in [1, 2, 3, 5, 10]:
    threshold_rows.append({
        "min_interactions": threshold,
        "users_below_threshold": int((user_interaction_counts < threshold).sum()),
        "users_eligible": int((user_interaction_counts >= threshold).sum()),
    })
threshold_df = pd.DataFrame(threshold_rows)
display(threshold_df)

print("[EDA] Distribusi tipe interaksi")
display(raw_interactions["type"].value_counts().head(15).rename_axis("type").to_frame("count"))

if "placeCategoryName" in raw_places.columns:
    print("[EDA] Top kategori tempat")
    display(raw_places["placeCategoryName"].fillna("-").value_counts().head(10).rename_axis("placeCategoryName").to_frame("count"))

numeric_place_cols = [col for col in ["placePrice", "placeRating"] if col in raw_places.columns]
if numeric_place_cols:
    print("[EDA] Statistik numerik places")
    place_numeric = raw_places[numeric_place_cols].apply(pd.to_numeric, errors="coerce")
    display(place_numeric.describe().T)

print("[EDA] Contoh data mentah places dan interactions")
display(raw_places.head(5))
display(raw_interactions.head(5))

fig, axes = plt.subplots(2, 2, figsize=(18, 12))

user_interaction_counts.head(10).sort_values().plot(kind="barh", ax=axes[0, 0], color="#0f766e")
axes[0, 0].set_title("Top 10 pengguna paling aktif")
axes[0, 0].set_xlabel("Jumlah interaksi")
axes[0, 0].set_ylabel("userId")

item_interaction_counts.head(10).sort_values().plot(kind="barh", ax=axes[0, 1], color="#7c3aed")
axes[0, 1].set_title("Top 10 item paling populer")
axes[0, 1].set_xlabel("Jumlah interaksi")
axes[0, 1].set_ylabel("refId")

user_interaction_counts.plot(kind="hist", bins=30, ax=axes[1, 0], color="#2563eb", edgecolor="white")
axes[1, 0].set_title("Distribusi jumlah interaksi per user")
axes[1, 0].set_xlabel("Interaksi per user")
axes[1, 0].set_ylabel("Frekuensi user")
axes[1, 0].set_yscale("log")

threshold_df.plot(x="min_interactions", y=["users_below_threshold", "users_eligible"], kind="line", marker="o", ax=axes[1, 1])
axes[1, 1].set_title("Cold-start profile per threshold")
axes[1, 1].set_xlabel("Minimum interaksi")
axes[1, 1].set_ylabel("Jumlah user")
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

metrics_for_chart = pd.Series({
    "density": density,
    "sparsity": sparsity,
    "gini_user": gini_coefficient(user_interaction_counts.values),
    "gini_item": gini_coefficient(item_interaction_counts.values),
})
metrics_for_chart.plot(kind="bar", ax=axes[0], color=["#22c55e", "#ef4444", "#3b82f6", "#f59e0b"])
axes[0].set_title("Metrik struktur data")
axes[0].set_ylim(0, 1)
axes[0].grid(True, axis="y", alpha=0.3)

raw_interactions["type"].value_counts().head(10).sort_values().plot(kind="barh", ax=axes[1], color="#8b5cf6")
axes[1].set_title("Top 10 tipe interaksi")
axes[1].set_xlabel("Jumlah")

if numeric_place_cols:
    place_numeric = raw_places[numeric_place_cols].apply(pd.to_numeric, errors="coerce")
    place_numeric.hist(ax=axes[2], bins=30, edgecolor="white")
    axes[2].set_title("Distribusi numerik places")
else:
    axes[2].axis("off")

plt.tight_layout()
plt.show()
```

+++ {"id": "7Vl6w--X0Ukk"}

# Preprocessing

```{code-cell} ipython3
---
colab:
  base_uri: https://localhost:8080/
id: nTGyLvzo0T47
outputId: e29306da-0c14-4edd-b884-c863bf3033ed
---
class ARTourDataPreprocessor:
    def __init__(self, config):
        self.config = config
        # Initialize as empty DataFrame to satisfy static checks before load
        self.df_places_master = pd.DataFrame()
        self.df_interactions_master = pd.DataFrame()
        self._load_and_clean_data()

    def _load_and_clean_data(self):
        print("[1/3] Mengambil dataset dari API...")
        df_p = fetch_places_df(self.config["API"]["places"], self.config["API"]["headers"])
        df_i = fetch_interactions_df(self.config["API"]["interactions"], self.config["API"]["headers"])

        # --- CLEANING PLACES & NLP MEMOIZATION ---
        print("[2/3] Memulai ekstraksi NLP (Sastrawi) dengan Memoization...")
        df_p['placePrice'] = pd.to_numeric(df_p['placePrice'], errors='coerce').fillna(0)
        df_p['placeRating'] = pd.to_numeric(df_p['placeRating'], errors='coerce').fillna(0)

        # 1. Agregasi Teks
        text_cols = ['placeName', 'placeCategoryName', 'placeDescription', 'placeAddress', 'placeHashtags']
        df_p['raw_combined'] = df_p[text_cols].fillna('').agg(' '.join, axis=1)

        # 2 & 3. Case Folding & RegEx (Hanya a-z dan spasi)
        df_p['clean_text'] = df_p['raw_combined'].str.lower()
        df_p['clean_text'] = df_p['clean_text'].apply(lambda x: re.sub(r'[^a-z\s]', ' ', str(x)))
        df_p['clean_text'] = df_p['clean_text'].apply(lambda x: re.sub(r'\s+', ' ', x).strip())

        # 4 & 5. Memoization Stopword & Stemming
        unique_words = set(" ".join(df_p['clean_text']).split())
        stemmer = StemmerFactory().create_stemmer()
        stopwords = set(StopWordRemoverFactory().get_stop_words())

        word_dict = {}
        for w in unique_words:
            if w not in stopwords:
                word_dict[w] = stemmer.stem(w) # Stemming hanya untuk kata unik
            else:
                word_dict[w] = ""

        # Mapping kamus unik kembali ke kalimat
        df_p['clean_text'] = df_p['clean_text'].apply(
            lambda x: " ".join([word_dict.get(w, "") for w in x.split() if word_dict.get(w, "") != ""]).strip()
        )
        self.df_places_master = df_p

        # --- CLEANING INTERACTIONS ---
        print("[3/3] Membersihkan jejak interaksi pengguna...")
        df_i['createdAt'] = pd.to_datetime(df_i['createdAt'])
        df_i = df_i.sort_values(by='createdAt')
        df_i['value'] = pd.to_numeric(df_i['value'], errors='coerce').fillna(0)

        # Deduplikasi Toggle
        def get_toggle_group(action_type):
            if action_type in ['PLACE_LIKE', 'PLACE_UNLIKE']: return 'TOGGLE_LIKE'
            if action_type in ['PLACE_BOOKMARK', 'PLACE_UNBOOKMARK']: return 'TOGGLE_BOOKMARK'
            if action_type in ['PLACE_DISLIKE', 'PLACE_UNDISLIKE']: return 'TOGGLE_DISLIKE'
            return action_type

        df_i['interaction_group'] = df_i['type'].apply(get_toggle_group)
        df_dedup = df_i.groupby(['userId', 'refId', 'interaction_group']).tail(1).copy()

        # Filter Interaksi Positif
        min_rev = self.config["PREPROCESSING"]["min_rating_positive"]
        valid_actions = ['PLACE_LIKE', 'PLACE_BOOKMARK', 'PLACE_SHARE']
        cond_review = (df_dedup['type'] == 'PLACE_REVIEW') & (df_dedup['value'] >= min_rev)
        cond_others = df_dedup['type'].isin(valid_actions)

        self.df_interactions_master = df_dedup[cond_review | cond_others].sort_values(by='createdAt')
        print("Pra-pemrosesan Selesai!")

    def get_filtered_data(self, min_interactions):
        """Metode ini dipanggil oleh evaluator untuk mengatur Cold-Start user secara dinamis"""
        df_valid = self.df_interactions_master[
            (self.df_interactions_master['refModule'] == 'PLACE') &
            (self.df_interactions_master['refId'].isin(self.df_places_master['placeId']))
        ].copy()

        user_counts = df_valid['userId'].value_counts()
        valid_users = user_counts[user_counts >= min_interactions].index
        df_filtered_int = df_valid[df_valid['userId'].isin(valid_users)].copy()

        return self.df_places_master.copy(), df_filtered_int

# Inisialisasi Singleton Preprocessor
preprocessor = ARTourDataPreprocessor(CONFIG)
```

+++ {"id": "KcFdCH2i0Zoy"}

# Recommender

```{code-cell} ipython3
---
colab:
  base_uri: https://localhost:8080/
id: tA8arGnh0c5N
outputId: 7483226e-ff4e-4157-914a-9d597aa0b606
---
# ==============================================================================
# SEL 2: MESIN INTI REKOMENDASI (ARTourRecommenderSystem)
# ==============================================================================
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from mlxtend.frequent_patterns import apriori, association_rules

class ARTourRecommenderSystem:
    def __init__(self, df_places, df_int, config, N, K):
        self.config = config
        self.N = N
        self.K = K
        self.df_places = df_places
        self.df_int = df_int

        self.catalog_places = self.df_places['placeId'].tolist()
        self.place_stats = self.df_places.set_index('placeId')[['placePrice', 'placeRating']].to_dict('index')
        self.min_price = self.df_places['placePrice'].min()
        self.max_price = self.df_places['placePrice'].max()

        self.place_id_to_idx = {pid: idx for idx, pid in enumerate(self.catalog_places)}
        self.idx_to_place_id = {idx: pid for idx, pid in enumerate(self.catalog_places)}

        self._prepare_sloo_split()
        self._build_cbf_models()
        self._build_apriori_rules()

    def _prepare_sloo_split(self):
        self.test_data = self.df_int.groupby('userId').tail(1)
        self.train_data = self.df_int.drop(self.test_data.index)

    def _build_cbf_models(self):
        self.vectorizer = TfidfVectorizer()
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df_places['clean_text'])

    def _build_apriori_rules(self):
        basket = self.train_data.groupby(['userId', 'refId'])['refId'].count().unstack().fillna(0)
        basket = (basket > 0)

        num_transactions = len(basket)
        abs_supp = self.config["APRIORI"]["min_absolute_support"]

        # Konversi dinamis Absolute ke Relative Support
        dynamic_min_support = abs_supp / num_transactions if num_transactions > 0 else 0.01

        freq_itemsets = apriori(basket, min_support=dynamic_min_support, use_colnames=True, max_len=self.config["APRIORI"]["k_max"])
        if not freq_itemsets.empty:
            self.rules = association_rules(freq_itemsets, metric="lift", min_threshold=1.0)
        else:
            self.rules = pd.DataFrame()

    def get_apriori_candidates(self, user_basket):
        if self.rules.empty:
            return []
        candidates = {}
        basket_set = frozenset(user_basket)

        for _, row in self.rules.iterrows():
            if row['antecedents'].issubset(basket_set):
                for item in row['consequents']:
                    if item not in basket_set:  # Item Masking (Otomatis)
                        if item not in candidates or row['lift'] > candidates[item]:
                            candidates[item] = row['lift']
        return sorted(candidates.keys(), key=lambda x: candidates[x], reverse=True)

    def get_cbf_candidates(self, user_basket, exclude_cands, needed, anchor_only=False):
        # Resolve basket indices (guard against missing ids)
        if anchor_only:
            last = user_basket[-1] if user_basket else None
            basket_indices = [self.place_id_to_idx[last]] if last and last in self.place_id_to_idx else []
        else:
            basket_indices = [self.place_id_to_idx[p] for p in user_basket if p in self.place_id_to_idx]

        if not basket_indices:
            return []

        # Build dense rows via vectorizer.transform on place text to avoid sparse matrix indexing
        dense_rows = []
        for idx in basket_indices:
            try:
                text = self.df_places.iloc[int(idx)]['clean_text']
            except Exception:
                text = ""
            vec = self.vectorizer.transform([str(text)])
            toarray = getattr(vec, 'toarray', None)
            if callable(toarray):
                arr = toarray()
                dense_rows.append(np.ravel(np.asarray(arr)))
            else:
                dense_rows.append(np.ravel(np.asarray(vec)))

        if not dense_rows:
            return []

        dense_subset = np.vstack(dense_rows)
        anchor_vector = dense_subset.mean(axis=0)
        anchor_vector = np.atleast_2d(anchor_vector.astype(float))

        sim_scores = cosine_similarity(anchor_vector, self.tfidf_matrix).flatten()
        top_indices = sim_scores.argsort()[::-1]

        cbf_cands = []
        for idx in top_indices:
            pid = self.idx_to_place_id.get(int(idx))
            if not pid:
                continue
            if pid not in user_basket and pid not in exclude_cands:  # Item Masking
                cbf_cands.append(pid)
                if len(cbf_cands) >= needed:
                    break
        return cbf_cands

    def rerank_mcrs(self, candidates, target_K):
        if not candidates:
            return []
        scored_cands = []

        c = self.config["MCRS"]
        for p in candidates:
            stats = self.place_stats.get(p)
            if not stats:
                continue

            norm_price = (stats['placePrice'] - self.min_price) / (self.max_price - self.min_price) if self.max_price > self.min_price else 0
            cost_score = 1.0 - norm_price

            raw_rating = stats['placeRating']
            if raw_rating is None or raw_rating == 0:
                benefit_score = c.get("neutral_rating_score", 0.5)
            else:
                norm_rating = (raw_rating - c["min_rating_scale"]) / (c["max_rating_scale"] - c["min_rating_scale"]) if (c["max_rating_scale"] > c["min_rating_scale"]) else 0.0
                benefit_score = max(0.0, min(1.0, norm_rating))

            final_score = c["weight_cost"] * cost_score + c["weight_benefit"] * benefit_score
            scored_cands.append((p, final_score))

        scored_cands.sort(key=lambda x: x[1], reverse=True)
        return [x[0] for x in scored_cands[:target_K]]
```

+++ {"id": "N5oKFGo80hRX"}

# Evaluate & Compare

```{code-cell} ipython3
---
colab:
  base_uri: https://localhost:8080/
id: CpSImQzS0jS5
outputId: 59682b28-e031-4620-8a3e-6e1fe7e64193
---
# ==============================================================================
# SEL 3: EVALUATOR KOMPREHENSIF (Ablation + Grid Search MCRS)
# ==============================================================================
from tqdm import tqdm
import numpy as np

class ARTourComprehensiveEvaluator:
    def __init__(self, base_system):
        self.base = base_system

        # Pre-compute Global Popularity dari Training Data
        pop_counts = self.base.train_data['refId'].value_counts()
        self.global_popularity = pop_counts.index.tolist()
        for p in self.base.catalog_places:
            if p not in self.global_popularity:
                self.global_popularity.append(p)

    def _get_popularity_cands(self, basket, target_K):
        cands = []
        for p in self.global_popularity:
            if p not in basket: # Item Masking
                cands.append(p)
                if len(cands) == target_K: break
        return cands

    def _calculate_metrics(self, all_recommended, hits, rr_sum, valid_users):
        hr = hits / valid_users if valid_users > 0 else 0
        mrr = rr_sum / valid_users if valid_users > 0 else 0

        total_items = len(self.base.catalog_places)
        cov = (len(set(all_recommended)) / total_items) * 100 if total_items > 0 else 0

        freq_array = np.zeros(total_items)
        for p in all_recommended:
            if p in self.base.place_id_to_idx:
                freq_array[self.base.place_id_to_idx[p]] += 1

        total_recs = np.sum(freq_array)
        if total_recs > 0 and len(freq_array) > 0:
            n = len(freq_array)
            p_array = freq_array / total_recs
            diff_matrix = np.abs(p_array[:, np.newaxis] - p_array[np.newaxis, :])
            diff_sum = np.sum(diff_matrix)
            mean_p = np.mean(p_array)

            # LOGIKA GINI WAJIB: n dikuadratkan
            gini = diff_sum / (2 * (n ** 2) * mean_p)
        else:
            gini = 0.0

        return hr, mrr, cov, gini

    def run_evaluation(self, nk_combinations):
        models = {}
        # Ekstrak semua nilai K unik dari kombinasi untuk membuat baseline Ablation Study
        unique_k_values = set([k for n, k in nk_combinations])

        # 1. Inisialisasi dictionary untuk Baseline (Ablation Study) per nilai K
        for k in sorted(unique_k_values):
            models[f"1. Popularity Only (K={k})"] = {"hits": 0, "rr": 0, "recs": []}
            models[f"2. Pure Apriori (K={k})"] = {"hits": 0, "rr": 0, "recs": []}
            models[f"3. Pure CBF (K={k})"] = {"hits": 0, "rr": 0, "recs": []}
            models[f"4. Apriori+CBF No MCRS (K={k})"] = {"hits": 0, "rr": 0, "recs": []}

        # 2. Inisialisasi dictionary untuk Hybrid MCRS (Grid Search)
        for N, K in nk_combinations:
            models[f"5. Hybrid MCRS (N={N}, K={K})"] = {"hits": 0, "rr": 0, "recs": []}

        valid_users = 0

        for user_id in tqdm(self.base.test_data['userId'].unique(), desc="Evaluasi Model", leave=False):
            test_row = self.base.test_data[self.base.test_data['userId'] == user_id].iloc[0]
            ground_truth = test_row['refId']

            basket = self.base.train_data[self.base.train_data['userId'] == user_id]['refId'].tolist()
            if not basket: continue

            valid_users += 1
            basket_set = set(basket)

            # Ekstrak Apriori Mentah (sekali saja per user agar hemat komputasi)
            apriori_raw = self.base.get_apriori_candidates(basket)
            apriori_filtered = [p for p in apriori_raw if p not in basket_set]

            # ==============================================================
            # A. EKSEKUSI BASELINE (ABLATION STUDY) UNTUK SETIAP K
            # ==============================================================
            for k in unique_k_values:
                # Model 1: Pop
                m1 = self._get_popularity_cands(basket_set, target_K=k)
                # Model 2: Apriori
                m2 = apriori_filtered[:k]
                # Model 3: CBF
                m3 = self.base.get_cbf_candidates(basket, exclude_cands=[], needed=k, anchor_only=True)
                # Model 4: Apriori + CBF Padding (Tanpa MCRS)
                m4 = list(m2)
                if len(m4) < k:
                    m4.extend(self.base.get_cbf_candidates(basket, m4, needed=k-len(m4), anchor_only=False))

                # Pencatatan Baseline
                baselines = {
                    f"1. Popularity Only (K={k})": m1, f"2. Pure Apriori (K={k})": m2,
                    f"3. Pure CBF (K={k})": m3, f"4. Apriori+CBF No MCRS (K={k})": m4
                }
                for name, cands in baselines.items():
                    models[name]["recs"].extend(cands)
                    if ground_truth in cands:
                        models[name]["hits"] += 1
                        models[name]["rr"] += (1.0 / (cands.index(ground_truth) + 1))

            # ==============================================================
            # B. EKSEKUSI HYBRID MCRS (GRID SEARCH N & K)
            # ==============================================================
            for N, K in nk_combinations:
                name = f"5. Hybrid MCRS (N={N}, K={K})"

                # Over-generation N
                hybrid_cands = list(apriori_filtered[:N])
                if len(hybrid_cands) < N:
                    hybrid_cands.extend(self.base.get_cbf_candidates(basket, hybrid_cands, N-len(hybrid_cands), False))

                # Truncation K
                m5 = self.base.rerank_mcrs(hybrid_cands, target_K=K)

                models[name]["recs"].extend(m5)
                if ground_truth in m5:
                    models[name]["hits"] += 1
                    models[name]["rr"] += (1.0 / (m5.index(ground_truth) + 1))

        # Hitung kalkulasi akhir metrik
        results = {}
        for m_name, data in models.items():
            results[m_name] = self._calculate_metrics(data["recs"], data["hits"], data["rr"], valid_users)

        return results, valid_users


# ==============================================================================
# AUTOMATIC RUNNER: ABLATION + GRID SEARCH
# ==============================================================================
if __name__ == "__main__":

    # -------------------------------------------------------------------------
    # PARAMETER EKSPERIMEN (Sesuai Permintaan Anda)
    # -------------------------------------------------------------------------
    MIN_INTERACTIONS_LIST = [2, 3]
    NK_SCENARIOS = [
        (5, 5),   # MCRS sebagai Shuffler
        (10, 5),  # Over-generation moderat
        (10, 10), # MCRS sebagai Shuffler di K tinggi
        (15, 10), # Over-generation moderat
        (20, 10)  # Over-generation maksimal
    ]

    for min_int in MIN_INTERACTIONS_LIST:
        print("\n" + "="*95)
        print(f"{'EVALUASI KOMPREHENSIF | COLD-START (Min Interaksi = ' + str(min_int) + ')':^95}")
        print("="*95)

        # Panggil data dari Preprocessor (Sel 1)
        df_p, df_i = preprocessor.get_filtered_data(min_interactions=min_int)

        # Init Sistem (Parameter N, K statis disini diabaikan karena ditimpa evaluator)
        sys_eval = ARTourRecommenderSystem(df_p, df_i, CONFIG, N=20, K=10)
        evaluator = ARTourComprehensiveEvaluator(sys_eval)

        # Jalankan
        results, valid_users = evaluator.run_evaluation(NK_SCENARIOS)

        print(f"Total Test Users Valid: {valid_users} users")
        print("-" * 95)
        print(f"{'Arsitektur Model':<35} | {'Hit Rate':<12} | {'MRR':<12} | {'Coverage (%)':<12} | {'Gini Index':<10}")
        print("-" * 95)

        # Sortir hasil: urutan numerik berdasarkan nomor model, lalu parameter K dan N
        def sort_key(name):
            m_num = re.match(r"(\d+)\.", name)
            model_num = int(m_num.group(1)) if m_num else 99
            n_match = re.search(r"N=(\d+)", name)
            k_match = re.search(r"K=(\d+)", name)
            n_val = int(n_match.group(1)) if n_match else 0
            k_val = int(k_match.group(1)) if k_match else 0
            return (model_num, k_val, n_val)

        sorted_names = sorted(results.keys(), key=sort_key)
        prev_model_num = None
        for name in sorted_names:
            hr, mrr, cov, gini = results[name]
            # Tambah garis pemisah antar grup model
            m_num = re.match(r"(\d+)\.", name)
            curr_model_num = int(m_num.group(1)) if m_num else 99
            if prev_model_num is not None and curr_model_num != prev_model_num:
                print("-" * 95)
            prev_model_num = curr_model_num
            print(f"{name:<35} | {hr:<12.4f} | {mrr:<12.4f} | {cov:<12.2f} | {gini:<10.4f}")

        print("="*95)
```
