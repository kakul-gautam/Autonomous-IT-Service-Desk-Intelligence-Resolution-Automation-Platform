"""
Data audit script for ticket datasets.

Produces basic statistics printed to stdout and writes a small JSON summary.
"""
from pathlib import Path
import csv
import json
import statistics


DATA_DIR = Path(__file__).resolve().parents[2] / 'ai_models' / 'datasets'
SRC = DATA_DIR / 'tickets_augmented.csv'
OUT = DATA_DIR / 'audit_summary.json'


def read_rows(path):
    rows = []
    if not path.exists():
        return rows
    with path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def main():
    rows = read_rows(SRC)
    n = len(rows)
    categories = {}
    lengths = []
    sample_per_cat = {}

    for r in rows:
        cat = (r.get('category') or 'Uncertain').strip()
        categories[cat] = categories.get(cat, 0) + 1
        issue = (r.get('issue') or '').strip()
        lengths.append(len(issue.split()))
        if cat not in sample_per_cat and issue:
            sample_per_cat[cat] = issue

    summary = {
        'rows': n,
        'categories': categories,
        'mean_length_words': statistics.mean(lengths) if lengths else 0,
        'median_length_words': statistics.median(lengths) if lengths else 0,
        'min_length_words': min(lengths) if lengths else 0,
        'max_length_words': max(lengths) if lengths else 0,
        'sample_per_category': sample_per_cat,
    }

    print(json.dumps(summary, indent=2))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open('w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print('\nWrote audit summary to:', OUT)


if __name__ == '__main__':
    main()
