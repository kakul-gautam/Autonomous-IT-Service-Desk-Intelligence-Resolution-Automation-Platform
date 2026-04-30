"""
Export tickets from the Django database into a CSV usable for training.

Creates `ai_models/datasets/tickets_from_db.csv` with columns: issue,category,solution

Usage (from project root):
    python -m ai_models.training.export_dataset

This script configures Django settings automatically and can be run inside
the project's virtualenv.
"""
import os
import csv
import django
from pathlib import Path


def export_dataset(output_dir: str | None = None) -> int:
    # Ensure we import Django settings from the project
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

    from tickets.models import Ticket

    project_root = Path(__file__).resolve().parents[2]
    output_base = Path(output_dir) if output_dir else Path(project_root) / 'ai_models' / 'datasets'
    output_base.mkdir(parents=True, exist_ok=True)
    output_path = output_base / 'tickets_from_db.csv'

    qs = Ticket.objects.exclude(suggested_solution__isnull=True).exclude(suggested_solution__exact='')
    count = qs.count()

    with output_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['issue', 'category', 'solution'])
        for t in qs.iterator():
            issue_text = ' '.join(filter(None, [getattr(t, 'title', ''), getattr(t, 'description', '')])).strip()
            category = t.category.strip() if getattr(t, 'category', None) else 'Uncertain'
            solution = t.suggested_solution.strip()
            if not issue_text or not solution:
                continue
            writer.writerow([issue_text, category, solution])

    print(f"Exported {count} tickets to: {output_path}")
    return int(count)


if __name__ == '__main__':
    exported = export_dataset()
    print('Done. Rows exported:', exported)
