<div align="center">

# 🤟 Signal — AI-Powered Sign Language Learning Platform

**Convert speech, text, and documents into sign language animations using artificial intelligence.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.1+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![Gemini](https://img.shields.io/badge/Google_Gemini-API-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-CDN-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

## 📋 Overview

**Signal** is a full-stack web application that bridges the communication gap between spoken/written language and sign language. It uses Google's Gemini AI to generate summaries, quizzes, and flashcards from uploaded documents—while converting text into animated Indian Sign Language (ISL) sequences in real time.

### Key Capabilities

| Feature | Description |
|---------|-------------|
| 🎤 **Live Speech-to-Sign** | Record audio via your microphone; the app transcribes it and plays matching sign language animations instantly. |
| 📄 **PPT/PDF Upload** | Upload PowerPoint or PDF files. The AI extracts content, generates a summary, and converts it to sign animations. |
| 🧠 **AI Summaries** | Google Gemini produces concise, structured summaries of uploaded documents. |
| 📝 **AI Quizzes** | Auto-generated multiple-choice quizzes with scoring, timers, and explanations to test retention. |
| 📊 **Dashboard** | Track uploads, view history, and monitor learning progress. |
| 🏆 **Gamification** | XP system, streaks, and skill-level badges to keep learners motivated. |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, Django 4.1+ |
| **AI Engine** | Google Gemini API (`google-genai`) |
| **NLP** | NLTK (tokenization, stopwords, lemmatization) |
| **Document Parsing** | `python-pptx` (PowerPoint), Pillow (images) |
| **Frontend** | HTML5, Tailwind CSS (CDN), Vanilla JavaScript |
| **Database** | SQLite (development) |
| **Fonts** | Inter (Google Fonts), Material Icons |

---

## 📁 Project Structure

```
Audio-Speech-To-Sign-Language-Converter/
│
├── A2SL/                        # Django project settings
│   ├── settings.py              # Project configuration
│   ├── urls.py                  # Root URL routing
│   ├── views.py                 # Auth views (login, signup, logout)
│   ├── wsgi.py                  # WSGI entry point
│   └── asgi.py                  # ASGI entry point
│
├── study_companion/             # Main application
│   ├── ai_services.py           # Gemini AI integration (summaries, quizzes)
│   ├── models.py                # Database models (PPTUpload)
│   ├── views.py                 # App views (dashboard, upload, summary, quiz)
│   ├── urls.py                  # App URL patterns
│   ├── admin.py                 # Django admin config
│   ├── tests.py                 # Unit tests
│   └── migrations/              # Database migrations
│
├── templates/                   # HTML templates
│   ├── home.html                # Landing page (standalone)
│   ├── login.html               # Login page (standalone)
│   ├── signup.html              # Signup page (standalone)
│   ├── base.html                # Base layout (sidebar + topbar)
│   ├── dashboard.html           # User dashboard
│   ├── upload_ppt.html          # File upload interface
│   ├── summary.html             # AI summary + sign language player
│   ├── animation.html           # Live speech-to-sign converter
│   ├── quiz.html                # Interactive quiz
│   ├── quiz_results.html        # Quiz results + XP
│   └── history.html             # Upload history
│
├── assets/                      # Static assets
│   └── ISL_Gifs/                # Indian Sign Language GIF animations
│
├── media/                       # User-uploaded files (gitignored)
├── manage.py                    # Django management script
├── requirements.txt             # Python dependencies
├── nltk_download.py             # NLTK data downloader script
├── setup.py                     # Package setup
├── .env                         # Environment variables (gitignored)
├── .gitignore                   # Git ignore rules
├── LICENSE                      # MIT License
└── README.md                    # This file
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **Google Gemini API Key** — [Get one free](https://ai.google.dev/)
- A modern browser (Chrome, Edge) with Web Speech API support

### 1. Clone the Repository

```bash
git clone https://github.com/jigargajjar55/Audio-Speech-To-Sign-Language-Converter.git
cd Audio-Speech-To-Sign-Language-Converter
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5. Download NLTK Data

```bash
python nltk_download.py
```

### 6. Apply Database Migrations

```bash
python manage.py migrate
```

### 7. Run the Development Server

```bash
python manage.py runserver
```

Open your browser → **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🎮 Usage Workflow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Landing     │────▶│  Sign Up /   │────▶│   Dashboard     │
│  Page        │     │  Log In      │     │                 │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                          ┌────────────────────────┼────────────────┐
                          ▼                        ▼                ▼
                   ┌──────────────┐     ┌──────────────┐   ┌──────────────┐
                   │  Upload PPT  │     │ Live Speech   │   │ View History │
                   │  / PDF       │     │ Converter     │   │              │
                   └──────┬───────┘     └──────────────┘   └──────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
       ┌──────────────┐      ┌──────────────┐
       │  AI Summary   │      │  AI Quiz     │
       │  + Sign Player│      │  + Results   │
       └──────────────┘      └──────────────┘
```

---

## ⚙️ Common Commands

| Command | Description |
|---------|-------------|
| `python manage.py runserver` | Start the development server |
| `python manage.py migrate` | Apply database migrations |
| `python manage.py createsuperuser` | Create an admin account |
| `python manage.py test study_companion` | Run unit tests |
| `python nltk_download.py` | Download required NLTK data |
| `pip install -r requirements.txt` | Install all dependencies |

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|---------|
| `ModuleNotFoundError: No module named 'django'` | Activate your virtual environment and run `pip install -r requirements.txt` |
| Database errors | Run `python manage.py migrate` to apply schema changes |
| Gemini API errors | Verify your `GEMINI_API_KEY` in `.env` is valid and has quota remaining |
| No sign language animations | Ensure the `assets/ISL_Gifs/` directory contains the GIF files |
| Web Speech API not working | Use Chrome or Edge; ensure microphone permissions are granted |

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ for accessible communication**

</div>
