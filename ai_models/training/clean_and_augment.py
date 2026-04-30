"""
Clean and augment ticket dataset for training.

Produces:
 - `ai_models/datasets/tickets_cleaned.csv`
 - `ai_models/datasets/tickets_augmented.csv`
 - `ai_models/datasets/train.csv`, `val.csv`, `test.csv`

Simple augmentation strategies used (deterministic, lightweight):
 - small character swap typo
 - randomly drop a non-stopword

This avoids external heavy dependencies and is suitable for quick dataset expansion.
"""
import os
import csv
import random
from pathlib import Path
import sys
import math

# Add project root to path to import preprocess
_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from ai_models.utils.preprocess import preprocess


DATA_DIR = _HERE / 'ai_models' / 'datasets'
SRC = DATA_DIR / 'tickets_from_db.csv'
CLEAN = DATA_DIR / 'tickets_cleaned.csv'
AUG = DATA_DIR / 'tickets_augmented.csv'

FALLBACKS = set([
    'Please contact IT support for further troubleshooting.',
    'No suggestion available',
])

CATEGORY_MAP = {
    'hardware': 'Hardware',
    'hw': 'Hardware',
    'software': 'Software',
    'sw': 'Software',
    'network': 'Network',
    'net': 'Network',
    'account': 'Account',
    'general': 'General',
    'uncertain': 'Uncertain',
}


def normalize_category(cat: str) -> str:
    if not isinstance(cat, str):
        return 'Uncertain'
    c = cat.strip().lower()
    return CATEGORY_MAP.get(c, cat.strip().title() or 'Uncertain')


def read_rows(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({'issue': r.get('issue','').strip(), 'category': r.get('category','').strip(), 'solution': r.get('solution','').strip()})
    return rows


def dedupe_and_filter(rows):
    seen = set()
    out = []
    for r in rows:
        sol = r['solution']
        if not sol or sol in FALLBACKS:
            continue
        issue = preprocess(r['issue'])
        if not issue:
            continue
        key = (issue, sol)
        if key in seen:
            continue
        seen.add(key)
        out.append({'issue': issue, 'category': normalize_category(r['category']), 'solution': sol})
    return out


def swap_two_chars(s: str) -> str:
    if len(s) < 3:
        return s
    i = random.randint(0, len(s)-2)
    lst = list(s)
    lst[i], lst[i+1] = lst[i+1], lst[i]
    return ''.join(lst)


def drop_word(s: str) -> str:
    parts = s.split()
    if len(parts) <= 3:
        return s
    # drop a middle word (not first/last)
    i = random.randint(1, len(parts)-2)
    parts.pop(i)
    return ' '.join(parts)


def augment_row(row, n=2, seed=42):
    random.seed(seed + hash(row['issue']) % 1000)
    aug = []
    for k in range(n):
        text = row['issue']
        # alternate augmentation strategies
        if k % 2 == 0:
            new = swap_two_chars(text)
        else:
            new = drop_word(text)
        aug.append({'issue': new, 'category': row['category'], 'solution': row['solution']})
    return aug


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['issue','category','solution'])
        for r in rows:
            writer.writerow([r['issue'], r['category'], r['solution']])


def split_rows(rows, val_frac=0.1, test_frac=0.1, seed=1):
    random.seed(seed)
    n = len(rows)
    idx = list(range(n))
    random.shuffle(idx)
    n_test = max(1, math.floor(n * test_frac))
    n_val = max(1, math.floor(n * val_frac))
    test_idx = set(idx[:n_test])
    val_idx = set(idx[n_test:n_test+n_val])
    train = [rows[i] for i in idx if i not in test_idx and i not in val_idx]
    val = [rows[i] for i in idx if i in val_idx]
    test = [rows[i] for i in idx if i in test_idx]
    return train, val, test


def main():
    print('Reading source:', SRC)
    rows = read_rows(SRC)
    print('Rows read:', len(rows))

    cleaned = dedupe_and_filter(rows)
    print('After dedupe/filter:', len(cleaned))
    write_csv(CLEAN, cleaned)
    print('Wrote cleaned:', CLEAN)

    # Augment
    augmented = list(cleaned)
    for r in cleaned:
        augmented.extend(augment_row(r, n=2))
    print('After augmentation:', len(augmented))
    write_csv(AUG, augmented)
    print('Wrote augmented:', AUG)

    # split
    train, val, test = split_rows(augmented)
    write_csv(DATA_DIR / 'train.csv', train)
    write_csv(DATA_DIR / 'val.csv', val)
    write_csv(DATA_DIR / 'test.csv', test)
    print('Wrote train/val/test splits:', len(train), len(val), len(test))


if __name__ == '__main__':
    main()
