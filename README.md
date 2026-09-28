<div align="center">

# 🤟 SignAI Pro — AI-Powered Indian Sign Language Platform

**A Modular, Feature-Based Platform for ISL Learning, Fingerspelling, and Concept Understanding Assessment.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.1+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Vision-00C4B4?style=for-the-badge)](https://developers.google.com/mediapipe)
[![Gemini](https://img.shields.io/badge/Google_Gemini-API-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-CDN-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)

</div>

---

## 📋 Overview

**SignAI Pro** is an assistive educational platform designed to empower Deaf learners and sign language students through AI-driven computer vision and natural language processing. The codebase is organized around a clean **feature-based architecture** where each capability is encapsulated into its own dedicated module.

---

## 🏗️ Feature-Based Project Structure

```
sign-project/
├── A2SL/                           # Core Project Configuration & WSGI
│   ├── settings.py                 # Installed apps, templates, static routes
│   └── urls.py                     # Root routing table including all feature apps
│
├── apps/                           # Modular Feature Packages
│   ├── accounts/                   # Authentication, user profile, password management
│   ├── dashboard/                  # Learning dashboard, user streaks, upload history
│   ├── upload/                     # PPTX/PDF/DOCX document text extraction & summary
│   ├── live_converter/             # Spoken English / Text to animated ISL sequence
│   ├── learning/                   # 5-section ISL course, lessons, and interactive practice
│   ├── quiz/                       # Document MCQs, Section Quizzes, and Sign Quest games
│   ├── sign_to_english/            # Live camera fingerspelling (A-Z) and word recognition
│   │   ├── recognition/            # Alphabet and sequence recognizer wrappers
│   │   ├── translation/            # Word builder and natural English translator
│   │   └── training/               # Offline training pipelines (train_alphabet.py, train_words.py)
│   └── concept_assessment/         # Student video explanation evaluation vs reference topic
│       └── services/               # Reference extraction, semantic comparison, graph alignment
│
├── shared/                         # Central Reusable Services
│   ├── ai/
│   │   └── gemini_service.py       # Centralized Gemini client & API wrapper
│   ├── sign_language/
│   │   ├── sign_recognition_service.py # Unified SignRecognitionService (used by both features)
│   │   ├── isl_preprocessing.py   # Canonical 86-dim hand landmark feature extractor
│   │   ├── temporal_model.py      # PyTorch BiGRU + Attention sequence classifier
│   │   └── vocabulary.py          # Controlled vocabulary registry
│   ├── utils/
│   │   └── validators.py          # Document and video file validators
│   └── templates/                 # Shared base templates (base.html)
│
├── models/                         # Pretrained Neural Network Weights & Configurations
│   └── sign_to_english/
│       ├── alphabet/               # isl_alphabet_model.pt, isl_alphabet_rf.joblib, labels
│       └── words/                  # isl_sequence_model.pt, model_config.json, labels
│
├── datasets/                       # Training Datasets & Landmarked Samples
│   ├── alphabets/                  # A-Z isolated landmark gesture datasets
│   └── words/                      # Controlled vocabulary gesture sequences
│
├── templates/                      # Feature-organized HTML templates
├── static/                         # Static CSS and JavaScript assets organized by feature
├── assets/                         # Video assets (.mp4) for sign dictionary & animations
├── media/                          # Uploaded documents and recorded concept videos
├── docs/                           # System architecture & pipeline documentation
│   └── architecture.md
└── manage.py
```

---

## 🚀 Quick Start Guide

### 1. Requirements & Prerequisites
- Python 3.10+ (tested on Python 3.11)
- Windows / macOS / Linux

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/pavan90303/sign-application.git
cd "sign project"

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate   # On Windows
# source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create or set your environment variables:
```bash
# Optional: Set Google Gemini API Key for AI summaries and quiz generation
set GEMINI_API_KEY=your_gemini_api_key_here
```
*(Note: If `GEMINI_API_KEY` is not provided, the platform automatically falls back to deterministic local NLP extraction).*

### 4. Database & Migrations
```bash
python manage.py migrate
```

### 5. Start Development Server
```bash
python manage.py runserver 127.0.0.1:8000
```
Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser.

---

## 🧪 Running System Checks & Tests

Run Django system validation:
```bash
python manage.py check
```

Run test suite:
```bash
python manage.py test
```

---

## 🤖 Machine Learning Models & Training

- **ISL Alphabet Model (A-Z)**:
  - Architecture: 86-dimensional geometric handshape classifier (`ISLAlphabetMLP`).
  - Pretrained weights: `models/sign_to_english/alphabet/isl_alphabet_model.pt`
  - Training script: `apps/sign_to_english/training/train_alphabet.py`

- **ISL Temporal Sequence Model**:
  - Architecture: BiGRU + Self-Attention (`ISLTemporalSequenceClassifier`).
  - Pretrained weights: `models/sign_to_english/words/isl_sequence_model.pt`
  - Training script: `apps/sign_to_english/training/train_words.py`

- **Shared Inference Service**:
  - Located in `shared/sign_language/sign_recognition_service.py`.
  - Reused by both **Sign-to-English** and **Concept Assessment** to eliminate code duplication.
