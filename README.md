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

## 🏗️ Architecture: Clean Frontend & Backend Separation

The project is cleanly decoupled into dedicated `frontend/` and `backend/` modules:

```
sign-project/
├── frontend/                           # UI Templates, Styles, Scripts & Animation Assets
│   ├── templates/                      # Organized HTML templates
│   │   ├── accounts/                   # Login, signup, user profile & editing
│   │   ├── dashboard/                  # Learning dashboard and history
│   │   ├── learning/                   # Course lessons and interactive practice
│   │   ├── quiz/                       # Quizzes, MCQs, and Sign Quest game
│   │   ├── sign_to_english/            # Live camera ISL fingerspelling recognition
│   │   ├── concept_assessment/         # Student video explanation & teacher review
│   │   ├── upload/                     # PPT/PDF document study material upload
│   │   ├── live_converter/             # Live English-to-sign animation converter
│   │   └── shared/                     # Master layout (base.html) & navbars
│   └── assets/                         # Static assets (CSS, JS, diagrams, sign videos)
│       ├── css/                        # Tailwind & custom CSS bundles
│       ├── js/                         # Client-side scripts & MediaPipe hooks
│       └── signs/                      # Production ISL animation video clips (.mp4)
│
├── backend/                            # Django Core, Feature Apps, AI/ML Services
│   ├── manage.py                       # Backend Django CLI runner
│   ├── A2SL/                           # Core configuration (settings.py, urls.py, wsgi.py)
│   ├── apps/                           # Modular feature apps (accounts, dashboard, etc.)
│   ├── shared/                         # Unified SignRecognitionService, Gemini AI, NLP
│   ├── study_companion/                # Course models, database handlers, migrations
│   ├── models/                         # Pretrained PyTorch & Random Forest weights
│   ├── datasets/                       # ISL alphabet and word training datasets
│   └── tests/                          # Backend unit & integration test suites
│
├── manage.py                           # Root runner (delegates to backend automatically)
├── requirements.txt                    # Python runtime dependencies
├── .env.example                        # Template for environment configuration
└── docs/                               # Architecture and system documentation
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
