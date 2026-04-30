"""
Quick trainer for small datasets (sanity-check use).

This script reads `ai_models/datasets/tickets_from_db.csv` and fits
word and char TF-IDF vectorizers, then saves artifacts to `ai_models/`.

Usage:
    python -m ai_models.training.train_quick
"""
import os
import sys
from pathlib import Path
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer


_ROOT = Path(__file__).resolve().parents[2]
DATASET = _ROOT / 'ai_models' / 'datasets' / 'tickets_from_db.csv'
OUTPUT_DIR = _ROOT / 'ai_models'


def load_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    df = pd.read_csv(path)
    df = df.dropna(subset=['issue', 'solution'])
    return df


def build_texts(df: pd.DataFrame):
    # Combine issue + category to match training pipeline
    combined = df['issue'].astype(str) + ' ' + df.get('category', '').astype(str)
    return combined.str.strip().tolist(), df['solution'].astype(str).tolist()


def train_quick():
    print('Loading dataset:', DATASET)
    df = load_dataset(DATASET)
    print('Rows:', len(df))
    texts, solutions = build_texts(df)

    # Lightweight word TF-IDF
    word_vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1,2), max_features=5000, sublinear_tf=True)
    word_matrix = word_vectorizer.fit_transform(texts)

    # Char-level TF-IDF
    char_vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3,5), max_features=8000, sublinear_tf=True)
    char_matrix = char_vectorizer.fit_transform(texts)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(word_vectorizer, OUTPUT_DIR / 'word_vectorizer.pkl')
    joblib.dump(word_matrix, OUTPUT_DIR / 'word_tfidf_matrix.pkl')
    joblib.dump(char_vectorizer, OUTPUT_DIR / 'char_vectorizer.pkl')
    joblib.dump(char_matrix, OUTPUT_DIR / 'char_tfidf_matrix.pkl')
    joblib.dump(solutions, OUTPUT_DIR / 'solutions.pkl')

    print('Artifacts saved to', OUTPUT_DIR)


if __name__ == '__main__':
    train_quick()
