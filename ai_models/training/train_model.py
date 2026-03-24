"""
Train IT ticket suggestion model using the 30,000-row enterprise dataset.

This trainer builds a hybrid retrieval model:
1) word-level TF-IDF (semantic matching)
2) character n-gram TF-IDF (typo and phrasing robustness)

Output artifacts (saved to ai_models/):
    word_vectorizer.pkl     — fitted word-level TfidfVectorizer
    word_tfidf_matrix.pkl   — sparse word-level document-term matrix
    char_vectorizer.pkl     — fitted char-level TfidfVectorizer
    char_tfidf_matrix.pkl   — sparse char-level document-term matrix
    solutions.pkl           — aligned solution strings
    categories.pkl          — aligned category strings

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
    categories     = df['category'].values

    # ── Word-level TF-IDF ────────────────────────────────────────
    print("Fitting word-level TF-IDF vectorizer...")
    word_vectorizer = TfidfVectorizer(
        stop_words='english',
        ngram_range=(1, 3),
        min_df=2,
        sublinear_tf=True,
        max_features=20000
    )
    word_tfidf_matrix = word_vectorizer.fit_transform(training_texts)
    print(f"  Word vocab size  : {len(word_vectorizer.vocabulary_)}")
    print(f"  Word matrix      : {word_tfidf_matrix.shape}")

    # ── Char-level TF-IDF (robust to typos / token variants) ─────
    print("Fitting char-level TF-IDF vectorizer...")
    char_vectorizer = TfidfVectorizer(
        analyzer='char_wb',
        ngram_range=(3, 5),
        min_df=2,
        sublinear_tf=True,
        max_features=30000
    )
    char_tfidf_matrix = char_vectorizer.fit_transform(training_texts)
    print(f"  Char vocab size  : {len(char_vectorizer.vocabulary_)}")
    print(f"  Char matrix      : {char_tfidf_matrix.shape}")

    # ── Save artifacts ───────────────────────────────────────────
    joblib.dump(word_vectorizer,   os.path.join(output_dir, 'word_vectorizer.pkl'))
    joblib.dump(word_tfidf_matrix, os.path.join(output_dir, 'word_tfidf_matrix.pkl'))
    joblib.dump(char_vectorizer,   os.path.join(output_dir, 'char_vectorizer.pkl'))
    joblib.dump(char_tfidf_matrix, os.path.join(output_dir, 'char_tfidf_matrix.pkl'))
    joblib.dump(solutions,         os.path.join(output_dir, 'solutions.pkl'))
    joblib.dump(categories,        os.path.join(output_dir, 'categories.pkl'))

    print("\nModel training completed successfully")
    print(f"  word_vectorizer.pkl   → {output_dir}")
    print(f"  word_tfidf_matrix.pkl → {output_dir}")
    print(f"  char_vectorizer.pkl   → {output_dir}")
    print(f"  char_tfidf_matrix.pkl → {output_dir}")
    print(f"  solutions.pkl         → {output_dir}")
    print(f"  categories.pkl        → {output_dir}")


if __name__ == '__main__':
    train_model()
