from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Case-based reasoning: find similar resolved tickets to assist with new issues
# Uses TF-IDF vectorization on ticket descriptions
# Confidence-aware automation: only suggest if similarity is high


def find_similar_tickets(new_ticket, all_tickets, top_n=3):
    """
    Find similar tickets using TF-IDF + cosine similarity.
    
    This implements case-based reasoning: learning from past resolved cases.
    
    Args:
        new_ticket: Ticket object with description
        all_tickets: QuerySet of all past Ticket objects
        top_n: Number of top similar tickets to return (default: 3)
    
    Returns:
        List of (ticket, similarity_score) tuples for top N similar tickets
    """
    
    # Need at least one ticket to compare against
    if not all_tickets.exists():
        return []
    
    # Collect descriptions
    descriptions = [new_ticket.description] + [t.description for t in all_tickets]
    
    # TF-IDF vectorization: converts text to numerical features
    vectorizer = TfidfVectorizer(
        max_features=100,
        stop_words='english',
        lowercase=True,
        min_df=1
    )
    
    try:
        tfidf_matrix = vectorizer.fit_transform(descriptions)
    except ValueError:
        # Handle edge case of very short text
        return []
    
    # Cosine similarity between new ticket (index 0) and all others
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
    
    # Get indices of top N similar tickets
    top_indices = similarities.argsort()[-top_n:][::-1]
    
    # Build result with similarity scores
    results = []
    for idx in top_indices:
        if similarities[idx] > 0.1:  # Minimum similarity threshold
            ticket = list(all_tickets)[idx]
            results.append((ticket, round(similarities[idx] * 100, 1)))
    
    return results


def compute_automation_confidence(similar_count):
    """
    Compute confidence score for automation.
    
    Confidence = min(similar_ticket_count * 30, 100)
    
    This is a simple heuristic: more similar cases = higher confidence
    """
    confidence = min(similar_count * 30, 100)
    return int(confidence)
