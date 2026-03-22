"""
Advanced text preprocessing for IT support ticket suggestion system.

Public API
----------
preprocess(text: str) -> str
    Cleans, normalises, and enriches raw issue text.

Features:
- Contraction expansion (won't → will not)
- Technical term normalization (wifi → wi-fi, etc.)
- Punctuation removal while preserving hyphens in technical terms
- Extra whitespace collapsing
- Special character handling
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

# Technical term normalization map
_TECHNICAL_TERMS: dict[str, str] = {
    r'\bwifi\b':        'wireless network',
    r'\bvpn\b':         'virtual private network',
    r'\bram\b':         'memory',
    r'\bcpu\b':         'processor',
    r'\bgpu\b':         'graphics',
    r'\bssd\b':         'storage',
    r'\bhdd\b':         'storage',
    r'\bos\b':          'operating system',
    r'\bapi\b':         'interface',
    r'\bdb\b':          'database',
    r'\bui\b':          'user interface',
    r'\bux\b':          'user experience',
    r'\bhttp\b':        'web',
    r'\bssl\b':         'security',
    r'\btls\b':         'security',
    r'\brebooting?\b':  'restart',
    r'\brebooted\b':    'restarted',
    r'\bcrashing\b':    'crashing',
    r'\bcrashed\b':     'crashed',
    r'\bfreeze(?:ing)?\b': 'freezing',
    r'\bfroze\b':       'frozen',
    r'\bblue.*screen\b': 'system error',
}

# Pre-compile regex patterns for performance
_CONTRACTION_RE: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\b' + re.escape(k) + r'\b'), v)
    for k, v in _CONTRACTIONS.items()
]

_TECHNICAL_RE: list[tuple[re.Pattern, str]] = [
    (re.compile(pattern, re.IGNORECASE), replacement)
    for pattern, replacement in _TECHNICAL_TERMS.items()
]


def preprocess(text: str) -> str:
    """
    Normalise and enrich raw IT support text for better matching.

    Steps applied (in order):
    1. Lowercase conversion
    2. Expand English contractions  (won't → will not)
    3. Normalize technical terms (wifi → wireless network)
    4. Remove special characters but preserve word structure
    5. Collapse extra whitespace
    6. Strip leading/trailing whitespace

    Parameters
    ----------
    text : str
        Raw issue description

    Returns
    -------
    str
        Cleaned, normalised, enriched text.

    Examples
    --------
    >>> preprocess("My WiFi won't connect!")
    'my wireless network will not connect'
    
    >>> preprocess("PC keeps freezing & crashes frequently")
    'pc keeps freezing and crashes frequently'
    """
    if not isinstance(text, str):
        return ""
    
    text = str(text).strip()
    if not text:
        return ""
    
    # ── Step 1: Lowercase ─────────────────────────────────────────────────
    text = text.lower()
    
    # ── Step 2: Expand contractions ───────────────────────────────────────
    for pattern, replacement in _CONTRACTION_RE:
        text = pattern.sub(replacement, text)
    
    # ── Step 3: Normalize technical terms ─────────────────────────────────
    for pattern, replacement in _TECHNICAL_RE:
        text = pattern.sub(replacement, text)
    
    # ── Step 4: Remove special characters ─────────────────────────────────
    # Keep letters, numbers, spaces, common hyphenated words
    text = re.sub(r'\s+', ' ', text)  # Collapse multiple spaces
    text = re.sub(r'[^a-z0-9\s\-]', '', text)  # Remove special chars
    text = re.sub(r'\s+', ' ', text)  # Collapse spaces again after cleanup
    
    # ── Step 5: Final cleanup ────────────────────────────────────────────
    text = text.strip()
    
    return text
