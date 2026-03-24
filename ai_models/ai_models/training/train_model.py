"""
Train IT ticket suggestion model using the 30,000-row enterprise dataset.
Combines issue + category text and applies contraction-aware preprocessing
before TF-IDF vectorisation for better fuzzy matching.

Output artifacts (saved to ai_models/):
    vectorizer.pkl    — fitted TfidfVectorizer
    tfidf_matrix.pkl  — sparse document-term matrix
    solutions.pkl     — aligned solution strings

Usage:
    python ai_models/training/train_model.py
"""

import os
import sys
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

# Allow importing from the ai_models package regardless of cwd
_AI_MODELS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AI_MODELS_DIR not in sys.path:
    sys.path.insert(0, os.path.dirname(_AI_MODELS_DIR))

from ai_models.utils.preprocess import preprocess


def load_dataset(dataset_path: str) -> pd.DataFrame:
    """Load and validate the CSV dataset."""
    df = pd.read_csv(dataset_path)
    required = {'issue', 'category', 'solution'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset missing columns: {missing}")
    df = df[list(required)].dropna()
    df = df[df['issue'].str.strip() != '']
    df = df[df['solution'].str.strip() != '']
    return df


def build_training_text(df: pd.DataFrame) -> list[str]:
    """
    Combine issue + category into one training string then preprocess.

    Example:
        issue    = "laptop not turning on"
        category = "Hardware"
        result   = "laptop not turning on hardware"
    """
    combined = df['issue'] + ' ' + df['category']
    return [preprocess(t) for t in combined]


def train_model() -> None:
    # ── Paths ────────────────────────────────────────────────────
    output_dir   = _AI_MODELS_DIR                         # ai_models/
    dataset_path = os.path.join(output_dir, 'datasets',
                                'enterprise_it_support_dataset_30000_rows.csv')

    # ── Load dataset ─────────────────────────────────────────────
    print("Loading dataset...")
    df = load_dataset(dataset_path)
    print(f"  Rows loaded      : {len(df)}")

    # ── Build training text ───────────────────────────────────────
    print("Preprocessing text (issue + category)...")
    training_texts = build_training_text(df)
    solutions      = df['solution'].values

    # ── TF-IDF Vectorizer ────────────────────────────────────────
    print("Fitting TF-IDF vectorizer...")
    vectorizer = TfidfVectorizer(
        stop_words='english',
        ngram_range=(1, 3),
        max_features=10000
    )
    tfidf_matrix = vectorizer.fit_transform(training_texts)
    print(f"  Vocabulary size  : {len(vectorizer.vocabulary_)}")
    print(f"  Matrix shape     : {tfidf_matrix.shape}")

    # ── Save artifacts ───────────────────────────────────────────
    joblib.dump(vectorizer,   os.path.join(output_dir, 'vectorizer.pkl'))
    joblib.dump(tfidf_matrix, os.path.join(output_dir, 'tfidf_matrix.pkl'))
    joblib.dump(solutions,    os.path.join(output_dir, 'solutions.pkl'))

    print("\nModel training completed successfully")
    print(f"  vectorizer.pkl   → {output_dir}")
    print(f"  tfidf_matrix.pkl → {output_dir}")
    print(f"  solutions.pkl    → {output_dir}")


if __name__ == '__main__':
    train_model()
