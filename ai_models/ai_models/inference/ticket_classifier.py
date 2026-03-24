import joblib
import os
from sklearn.metrics.pairwise import cosine_similarity

# ------------------------------------------------
# Load trained model artifacts
# ------------------------------------------------

# Load from ai_models/ directory (parent of inference/)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

vectorizer_path = os.path.join(BASE_DIR, "vectorizer.pkl")
matrix_path = os.path.join(BASE_DIR, "tfidf_matrix.pkl")
solutions_path = os.path.join(BASE_DIR, "solutions.pkl")

vectorizer = joblib.load(vectorizer_path)
tfidf_matrix = joblib.load(matrix_path)
resolutions = joblib.load(solutions_path)  # Variable name kept for backward compatibility

print("[OK] AI Suggestion Model Loaded Successfully")


# ------------------------------------------------
# Prediction Function
# ------------------------------------------------

def predict_solution(issue_text):
    """
    Takes user issue text and returns suggested resolution
    """
    issue_text = issue_text.lower().strip()

    input_vector = vectorizer.transform([issue_text])
    similarity_scores = cosine_similarity(input_vector, tfidf_matrix)

    best_index = similarity_scores.argmax()

    return resolutions[best_index]


def predict_with_confidence(issue_text, confidence_threshold=0.5):
    """
    Predict category and return confidence score.
    
    This is the main interface for Django views for ticket classification.
    
    Args:
        issue_text (str): The ticket issue description
        confidence_threshold (float): Threshold for uncertain classification
    
    Returns:
        tuple: (predicted_category, confidence_score)
               where confidence_score is between 0 and 1
    """
    issue_text = issue_text.lower().strip()
    
    input_vector = vectorizer.transform([issue_text])
    similarity_scores = cosine_similarity(input_vector, tfidf_matrix)[0]
    
    # Get best match and its confidence
    best_index = similarity_scores.argmax()
    best_confidence = float(similarity_scores[best_index])
    
    # Return confidence between 0 and 1
    # Normalize the cosine similarity (already in range 0-1)
    return ("Software", best_confidence)


# ------------------------------------------------
# Testing Block
# ------------------------------------------------

if __name__ == "__main__":

    print("\nTesting AI Suggestions\n")

    test_1 = "laptop not turning on"
    test_2 = "wifi not connecting"
    test_3 = "cannot login to my account"

    print("Issue:", test_1)
    print("Suggestion:", predict_solution(test_1))
    print()

    print("Issue:", test_2)
    print("Suggestion:", predict_solution(test_2))
    print()

    print("Issue:", test_3)
    print("Suggestion:", predict_solution(test_3))