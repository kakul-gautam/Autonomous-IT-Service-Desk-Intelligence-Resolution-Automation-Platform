"""
Combine real and synthetic datasets, clean, augment, split, and save.

Outputs:
 - ai_models/datasets/combined_final.csv (all rows)
 - ai_models/datasets/train_final.csv, val_final.csv, test_final.csv (splits)
"""
import csv
import random
import math
from pathlib import Path
from collections import Counter
import sys

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from ai_models.utils.preprocess import preprocess


DATA_DIR = _HERE / 'ai_models' / 'datasets'


def read_csv(path):
    rows = []
    if not path.exists():
        return rows
    with path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def dedupe_and_filter(rows):
    """Dedupe and remove low-quality rows."""
    seen = set()
    fallbacks = {
        'Please contact IT support for further troubleshooting.',
        'No suggestion available',
        'The issue category couldn\'t be determined with confidence. General troubleshooting: 1. Restart your device. 2. Check all cables and connections. 3. Review recent changes/updates. 4. Contact IT support with more details.',
    }
    out = []
    for r in rows:
        sol = (r.get('solution') or '').strip()
        if not sol or sol in fallbacks:
            continue
        issue = preprocess(r.get('issue', ''))
        if not issue:
            continue
        cat = (r.get('category') or 'Uncertain').strip().title()
        key = (issue, sol[:50])
        if key in seen:
            continue
        seen.add(key)
        out.append({'issue': issue, 'category': cat, 'solution': sol})
    return out


def swap_two_chars(s):
    if len(s) < 3:
        return s
    i = random.randint(0, len(s)-2)
    lst = list(s)
    lst[i], lst[i+1] = lst[i+1], lst[i]
    return ''.join(lst)


def drop_word(s):
    parts = s.split()
    if len(parts) <= 3:
        return s
    i = random.randint(1, len(parts)-2)
    parts.pop(i)
    return ' '.join(parts)


def augment_row(row, n=2, seed=42):
    """Generate augmented versions of a row."""
    random.seed(seed + hash(row['issue']) % 1000)
    aug = []
    for k in range(n):
        text = row['issue']
        new = swap_two_chars(text) if k % 2 == 0 else drop_word(text)
        aug.append({'issue': new, 'category': row['category'], 'solution': row['solution']})
    return aug


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['issue', 'category', 'solution'])
        writer.writeheader()
        writer.writerows(rows)


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
    print('Reading real data...')
    real_rows = read_csv(DATA_DIR / 'tickets_cleaned.csv')
    print('Real rows:', len(real_rows))
    
    print('Reading synthetic data...')
    synthetic_rows = read_csv(DATA_DIR / 'tickets_synthetic_large.csv')
    print('Synthetic rows:', len(synthetic_rows))
    
    # Combine
    all_rows = real_rows + synthetic_rows
    print('Combined rows:', len(all_rows))
    
    # Clean
    print('Deduping and filtering...')
    cleaned = dedupe_and_filter(all_rows)
    print('After dedup:', len(cleaned))
    
    # Augment
    print('Augmenting...')
    augmented = list(cleaned)
    for r in cleaned:
        augmented.extend(augment_row(r, n=2))
    print('After augmentation:', len(augmented))
    
    # Write combined
    write_csv(DATA_DIR / 'combined_final.csv', augmented)
    
    # Split
    train, val, test = split_rows(augmented, val_frac=0.1, test_frac=0.1)
    write_csv(DATA_DIR / 'train_final.csv', train)
    write_csv(DATA_DIR / 'val_final.csv', val)
    write_csv(DATA_DIR / 'test_final.csv', test)
    print(f'Wrote splits: train={len(train)}, val={len(val)}, test={len(test)}')
    
    # Stats
    cat_counts = Counter(r['category'] for r in augmented)
    print('Category distribution:', dict(cat_counts))
    
    sol_counts = Counter(r['solution'] for r in augmented)
    print('Top 5 solutions:')
    for sol, count in sol_counts.most_common(5):
        print(f'  {count}x : {sol[:60]}...')


if __name__ == '__main__':
    main()
