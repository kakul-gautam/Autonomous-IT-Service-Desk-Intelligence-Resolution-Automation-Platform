# AI Models

This folder separates machine learning assets from Django apps.

## Structure

- datasets/: CSV datasets used for training and evaluation
- training/: scripts that generate or train models
- inference/: model code used by Django at runtime
- utils/: shared helpers (if needed)

## Model Lifecycle

1. Data generation or collection
   - Synthetic data is generated locally for academic/demo usage.
   - Real enterprise data is not stored in this project.

2. Training
   - Training scripts live in training/.
   - Outputs are saved to datasets/ or model artifacts (if added later).

3. Inference
   - Django apps import inference modules directly.
   - Models load datasets at server startup for consistent predictions.

## Why Separation

- Keeps Django apps focused on web concerns (views, models, templates).
- Keeps ML code focused on training and inference logic.
- Enables independent ML iteration without touching app structure.
- Improves maintainability and clarity for teams.
