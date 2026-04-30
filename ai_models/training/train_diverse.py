"""
Create a train_reranker_diverse.py that uses the tickets_diverse.csv dataset
instead of the combined_final.csv dataset.
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import joblib
from ai_models.utils.preprocess import preprocess_text

print("=" * 80)
print("TRAINING MODEL WITH DIVERSE DATASET (650 ROWS, 20 UNIQUE SOLUTIONS PER CATEGORY)")
print("=" * 80)

# Load diverse dataset
diverse_path = Path(__file__).parent / 'ai_models' / 'datasets' / 'tickets_diverse.csv'
df = pd.read_csv(diverse_path)

print(f"\n📊 Dataset loaded: {len(df)} rows")
print(f"   Category distribution:")
for cat, count in df['category'].value_counts().items():
    print(f"      {cat}: {count} rows")

print(f"\n   Solutions per category:")
for cat, count in df.groupby('category')['solution'].nunique().items():
    print(f"      {cat}: {count} unique solutions")

# Preprocess
print("\n🔄 Preprocessing text...")
df['issue_preprocessed'] = df['issue'].apply(preprocess_text)

# Split 70-15-15
np.random.seed(42)
n = len(df)
train_size = int(0.7 * n)
val_size = int(0.15 * n)

perm = np.random.permutation(n)
train_idx, val_idx, test_idx = perm[:train_size], perm[train_size:train_size+val_size], perm[train_size+val_size:]

train_df = df.iloc[train_idx].reset_index(drop=True)
val_df = df.iloc[val_idx].reset_index(drop=True)
test_df = df.iloc[test_idx].reset_index(drop=True)

print(f"\n✅ Split: Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)}")

# Build vectorizers
print("\n🔨 Building vectorizers...")
word_vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1,2), sublinear_tf=True, stop_words='english')
char_vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3,5), max_features=15000)

word_vectorizer.fit(train_df['issue_preprocessed'])
char_vectorizer.fit(train_df['issue_preprocessed'])

# Vectorize
X_train_word = word_vectorizer.transform(train_df['issue_preprocessed'])
X_train_char = char_vectorizer.transform(train_df['issue_preprocessed'])

X_test_word = word_vectorizer.transform(test_df['issue_preprocessed'])
X_test_char = char_vectorizer.transform(test_df['issue_preprocessed'])

# Create training pairs
print("🔄 Creating training pairs...")
def create_training_pairs(df, X_word, X_char):
    pairs_X = []
    pairs_y = []
    solutions = df['solution'].tolist()
    categories = df['category'].tolist()
    
    for i in range(len(df)):
        issue_word_vec = X_word[i].toarray().flatten()
        issue_char_vec = X_char[i].toarray().flatten()
        issue_cat = categories[i]
        
        for j in range(len(df)):
            candidate_word_vec = X_word[j].toarray().flatten()
            candidate_char_vec = X_char[j].toarray().flatten()
            candidate_cat = categories[j]
            
            word_sim = np.dot(issue_word_vec, candidate_word_vec) / (np.linalg.norm(issue_word_vec) * np.linalg.norm(candidate_word_vec) + 1e-8)
            char_sim = np.dot(issue_char_vec, candidate_char_vec) / (np.linalg.norm(issue_char_vec) * np.linalg.norm(candidate_char_vec) + 1e-8)
            cat_match = 1.0 if issue_cat == candidate_cat else 0.0
            sol_freq = solutions[j].count(solutions[j][:10]) / len(df)
            
            pairs_X.append([word_sim, char_sim, cat_match, sol_freq])
            pairs_y.append(1 if i == j else 0)
    
    return np.array(pairs_X), np.array(pairs_y)

pairs_X, pairs_y = create_training_pairs(train_df, X_train_word, X_train_char)
print(f"   Training pairs: {pairs_X.shape}, Positive: {np.sum(pairs_y)}")

# Scale
scaler = StandardScaler()
pairs_X_scaled = scaler.fit_transform(pairs_X)

# Train
print("🔨 Training logistic regression re-ranker...")
clf = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
clf.fit(pairs_X_scaled, pairs_y)

# Evaluate
print("\n📊 Evaluating...")
pairs_X_test, pairs_y_test = create_training_pairs(test_df, X_test_word, X_test_char)
pairs_X_test_scaled = scaler.transform(pairs_X_test)
test_acc = clf.score(pairs_X_test_scaled, pairs_y_test)
print(f"   Test accuracy: {test_acc:.3f}")

# Save artifacts
print("\n💾 Saving artifacts...")
artifacts_dir = Path(__file__).parent / 'ai_models' / 'reranker_artifacts_v3_diverse'
artifacts_dir.mkdir(parents=True, exist_ok=True)

joblib.dump(word_vectorizer, artifacts_dir / 'word_vectorizer.pkl')
joblib.dump(char_vectorizer, artifacts_dir / 'char_vectorizer.pkl')
joblib.dump(clf, artifacts_dir / 'reranker_clf.pkl')
joblib.dump(scaler, artifacts_dir / 'feature_scaler.pkl')
joblib.dump(train_df.to_dict('list'), artifacts_dir / 'train_rows.pkl')

print(f"✅ Model artifacts saved to: {artifacts_dir}")
print("\n🎉 SUCCESS! Model trained with diverse dataset!")
print("   Dataset: 650 samples with 10-20 unique solutions per category")
print("   Your model will now provide better, more varied suggestions!")
