# Datasets Directory

This directory organizes training datasets for ISL models, cleanly isolated from static assets and web endpoints.

## Structure
- `datasets/alphabets/`: ISL alphabet (A-Z) gesture landmarks and feature vectors extracted from video samples.
- `datasets/words/`: ISL word and sentence gesture sequences for temporal sequence models (BiGRU/Transformer).

Data extraction and feature preprocessing pipeline:
- See `shared/sign_language/isl_preprocessing.py`
- See `apps/sign_to_english/training/train_alphabet.py`
- See `apps/sign_to_english/training/train_words.py`
