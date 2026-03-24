"""
Train IT ticket suggestion model using cleaned dataset.
Uses TF-IDF vectorization for text similarity matching.
"""

import pandas as pd
import joblib
import os
from sklearn.feature_extraction.text import TfidfVectorizer


def train_suggestion_model():
    """Train and save the ticket suggestion model."""
    
    print("="*60)
    print("IT Ticket Suggestion Model Training")
    print("="*60)
    
    # Define paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_path = os.path.join(base_dir, 'datasets', 'it_support_dataset_4000_rows.csv')
    inference_dir = os.path.join(base_dir, 'inference')
    
    # Create inference directory if it doesn't exist
    os.makedirs(inference_dir, exist_ok=True)
    
    # Load cleaned dataset
    print(f"\nLoading dataset from: {dataset_path}")
    df = pd.read_csv(dataset_path)
    print(f"Total samples loaded: {len(df)}")
    
    # Remove any remaining NaN or empty values
    df = df.dropna()
    df = df[df['issue_text'].str.strip() != '']
    df = df[df['resolution'].str.strip() != '']
    print(f"Samples after removing empty values: {len(df)}")
    
    # Extract features and labels
    X = df['issue_text'].values
    y = df['resolution'].values
    
    print(f"\nDataset shape:")
    print(f"  Issues (X): {len(X)}")
    print(f"  Resolutions (y): {len(y)}")
    
    # Initialize TF-IDF vectorizer
    print("\nInitializing TF-IDF vectorizer...")
    vectorizer = TfidfVectorizer(
        stop_words='english',
        ngram_range=(1, 2),
        max_features=5000
    )
    
    # Fit and transform the issue text
    print("Fitting vectorizer on issue text...")
    tfidf_matrix = vectorizer.fit_transform(X)
    
    print(f"\nTF-IDF matrix shape: {tfidf_matrix.shape}")
    print(f"Number of features: {len(vectorizer.get_feature_names_out())}")
    
    # Save model artifacts
    print("\nSaving model artifacts...")
    
    vectorizer_path = os.path.join(inference_dir, 'vectorizer.pkl')
    tfidf_matrix_path = os.path.join(inference_dir, 'tfidf_matrix.pkl')
    resolutions_path = os.path.join(inference_dir, 'resolutions.pkl')
    
    joblib.dump(vectorizer, vectorizer_path)
    print(f"  ✓ Vectorizer saved to: {vectorizer_path}")
    
    joblib.dump(tfidf_matrix, tfidf_matrix_path)
    print(f"  ✓ TF-IDF matrix saved to: {tfidf_matrix_path}")
    
    joblib.dump(y, resolutions_path)
    print(f"  ✓ Resolutions saved to: {resolutions_path}")
    
    # Print training statistics
    print("\n" + "="*60)
    print("TRAINING STATISTICS")
    print("="*60)
    print(f"Total training samples: {len(X)}")
    print(f"TF-IDF features generated: {tfidf_matrix.shape[1]}")
    print(f"Vocabulary size: {len(vectorizer.vocabulary_)}")
    print(f"Matrix sparsity: {(1 - tfidf_matrix.nnz / (tfidf_matrix.shape[0] * tfidf_matrix.shape[1])) * 100:.2f}%")
    
    # Show sample features
    print(f"\nSample TF-IDF features:")
    feature_names = vectorizer.get_feature_names_out()
    for i in range(min(10, len(feature_names))):
        print(f"  - {feature_names[i]}")
    
    print("\n" + "="*60)
    print("Training completed successfully!")
    print("="*60)
    print("\nThe model is ready for inference.")
    print("Use ai_models/inference/vectorizer.pkl for predictions.")


if __name__ == "__main__":
    train_suggestion_model()
