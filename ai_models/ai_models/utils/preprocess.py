"""
Text preprocessing utilities for the IT support ticket suggestion system.

Public API
----------
preprocess(text: str) -> str
    Cleans and normalises raw issue text before TF-IDF vectorisation.
"""

import re

# ---------------------------------------------------------------------------
# Contraction expansion map (applied after lowercasing)
# ---------------------------------------------------------------------------
_CONTRACTIONS: dict[str, str] = {
    "won't":    "will not",
    "can't":    "cannot",
    "couldn't": "could not",
    "wouldn't": "would not",
    "shouldn't":"should not",
    "mustn't":  "must not",
    "mightn't": "might not",
    "needn't":  "need not",
    "shan't":   "shall not",
    "isn't":    "is not",
    "aren't":   "are not",
    "wasn't":   "was not",
    "weren't":  "were not",
    "haven't":  "have not",
    "hasn't":   "has not",
    "hadn't":   "had not",
    "don't":    "do not",
    "doesn't":  "does not",
    "didn't":   "did not",
    "i'm":      "i am",
    "i've":     "i have",
    "i'll":     "i will",
    "i'd":      "i would",
    "you're":   "you are",
    "you've":   "you have",
    "you'll":   "you will",
    "you'd":    "you would",
    "he's":     "he is",
    "she's":    "she is",
    "it's":     "it is",
    "that's":   "that is",
    "there's":  "there is",
    "here's":   "here is",
    "what's":   "what is",
    "where's":  "where is",
    "who's":    "who is",
    "how's":    "how is",
    "we're":    "we are",
    "we've":    "we have",
    "we'll":    "we will",
    "we'd":     "we would",
    "they're":  "they are",
    "they've":  "they have",
    "they'll":  "they will",
    "they'd":   "they would",
    "let's":    "let us",
    "that'll":  "that will",
    "could've": "could have",
    "would've": "would have",
    "should've":"should have",
    "might've": "might have",
    "must've":  "must have",
    "o'clock":  "o clock",
}

# Pre-compile one regex per contraction for performance
_CONTRACTION_RE: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\b' + re.escape(k) + r'\b'), v)
    for k, v in _CONTRACTIONS.items()
]


def preprocess(text: str) -> str:
    """
    Normalise raw text for TF-IDF vectorisation.

    Steps applied (in order):
    1. Lowercase
    2. Expand English contractions  (won't → will not)
    3. Remove punctuation / special characters
    4. Collapse extra whitespace

    Parameters
    ----------
    text : str

    Returns
    -------
    str
        Cleaned, normalised text.

    Examples
    --------
    >>> preprocess("My computer won't turn on")
    'my computer will not turn on'
    >>> preprocess("Can't connect to VPN!!!")
    'cannot connect to vpn'
    """
    text = str(text).lower()
    for pattern, replacement in _CONTRACTION_RE:
        text = pattern.sub(replacement, text)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
