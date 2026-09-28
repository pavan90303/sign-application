# SignAI Pro Architecture & Technical Specification

## 1. Project Overview & Design Principles
SignAI Pro is a modular, feature-based assistive learning platform for Indian Sign Language (ISL).
The architecture strictly enforces:
- **One Feature → One Organized Feature Module**: Views, URLs, services, and tests are isolated within dedicated apps under `apps/`.
- **Single Source of Truth for Sign Recognition**: Both the live Sign-to-English translator and the Concept Assessment feature share a single, unified `SignRecognitionService` under `shared/sign_language/`.
- **Database Safety & Integrity**: Core database tables and migrations remain stable in `study_companion`, with feature apps interfacing via clean service boundaries without risking data loss.
- **Zero Hallucination & Honest Reporting**: High-confidence detection gates reject resting hands and noise; fallback logic uses local deterministic NLP when Gemini is unavailable.

---

## 2. Directory Structure

```
sign-project/
├── A2SL/                           # Django project root (settings, routing, wsgi)
│   ├── settings.py                 # Installed apps, templates, static directories
│   ├── urls.py                     # Main URL dispatcher including feature modules
│   └── wsgi.py
│
├── apps/                           # Feature-Based Modules
│   ├── accounts/                   # Authentication & user profile management
│   │   ├── apps.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── dashboard/                  # Learning analytics & upload history
│   │   ├── apps.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── upload/                     # Educational document ingestion & processing
│   │   ├── apps.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── services/               # document_extractor.py, summarizer.py
│   ├── live_converter/             # Spoken English / Text to ISL animation
│   │   ├── apps.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── services/               # nlp_processor.py
│   ├── learning/                   # Course curriculum, lessons, & interactive practice
│   │   ├── apps.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── services/
│   ├── quiz/                       # Section quizzes, Dino runner, & Sign Quest games
│   │   ├── apps.py
│   │   ├── prompts.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── services/               # quiz_generator.py, quest_generator.py
│   ├── sign_to_english/            # Live camera fingerspelling & word recognition
│   │   ├── apps.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── recognition/            # alphabet_recognizer.py, sequence_recognizer.py
│   │   ├── translation/            # word_builder.py, english_builder.py
│   │   └── training/               # train_alphabet.py, train_words.py
│   └── concept_assessment/         # Video explanation evaluation vs reference concept
│       ├── apps.py
│       ├── prompts.py
│       ├── urls.py
│       ├── views.py
│       └── services/               # video_processor.py, reference_processor.py,
│                                   # transcript_processor.py, concept_extractor.py,
│                                   # concept_comparator.py, graph_generator.py
│
├── shared/                         # Centralized Reusable Utilities & AI Services
│   ├── ai/
│   │   └── gemini_service.py       # Reusable Gemini client & call wrappers
│   ├── sign_language/
│   │   ├── sign_recognition_service.py # Authoritative unified SignRecognitionService
│   │   ├── isl_preprocessing.py   # Canonical 86-dim handshape feature extractor
│   │   ├── temporal_model.py      # PyTorch BiGRU + Attention sequence classifier
│   │   ├── isl_feature_extractor.py # Window normalization & shape validator
│   │   └── vocabulary.py          # Controlled vocabulary single source of truth
│   ├── utils/
│   │   └── validators.py          # Document & video upload validators
│   └── templates/                 # Shared base templates (base.html)
│
├── models/                         # Trained ML/DL Model Weights & Configs
│   └── sign_to_english/
│       ├── alphabet/               # isl_alphabet_model.pt, isl_alphabet_rf.joblib,
│       │                           # alphabet_labels.json, hand_landmarker.task
│       └── words/                  # isl_sequence_model.pt, labels.json, model_config.json
│
├── datasets/                       # Organized Training Datasets
│   ├── README.md
│   ├── alphabets/                  # A-Z landmark dataset directories
│   └── words/                      # Controlled word gesture sample directories
│
├── assets/                         # Video clips (.mp4) for sign dictionary & animations
├── media/                          # User uploads (ppt_uploads, concept_videos)
├── templates/                      # Templates organized by feature and global roots
├── static/                         # Static assets organized by feature
├── docs/                           # Architectural and design documentation
└── manage.py
```

---

## 3. Feature Ownership Map

| Feature | Primary URL | Core View / Action | Services |
| :--- | :--- | :--- | :--- |
| **Accounts** | `/login/`, `/signup/`, `/profile/` | Authentication, profile updates, password change | Django Auth, UserProfile |
| **Dashboard** | `/dashboard/`, `/history/` | Streak metrics, vocabulary mastery, upload history | UserProfile, CourseProgress |
| **Upload** | `/upload/`, `/summary/<id>/` | Ingest PPTX/PDF/DOCX, generate summary & sign breakdown | `document_extractor.py`, `summarizer.py` |
| **Live Converter**| `/live-converter/` | Convert spoken/typed English to sign animation | `nlp_processor.py` |
| **Learning** | `/learn/`, `/learn/section/<id>/` | 5-section ISL course, lessons, interactive practice | `course_data.py`, `sign_recognition.py` |
| **Quiz** | `/quiz/<id>/`, `/learn/.../quiz/` | Document MCQs, Section Quizzes, Sign Quest game | `quiz_generator.py`, `quest_generator.py` |
| **Sign to English** | `/sign-to-english/` | Real-time alphabet fingerspelling & word signs | `SignRecognitionService`, `word_builder.py` |
| **Concept Assessment** | `/concept-assessment/` | Evaluate student video explanation vs reference topic | `video_processor.py`, `concept_comparator.py` |

---

## 4. Shared Sign Recognition Pipeline

Both **Sign to English** and **Concept Assessment** reuse the authoritative `SignRecognitionService`:

```
Input Video / Camera Stream
            ↓
      OpenCV Frames
            ↓
  MediaPipe HandLandmarker (21 3D keypoints per hand)
            ↓
Geometric Canonicalization (Handedness mirroring, wrist centering, palm scaling)
            ↓
   ┌────────────────────────────────┴────────────────────────────────┐
   ↓                                                                 ↓
Alphabet Pipeline (Single-Frame Static)          Temporal Sequence Pipeline (16-Frame BiGRU)
   • 86-dim geometric feature vector                • 126-dim temporal landmark sequence
   • PyTorch ISLAlphabetMLP (A-Z)                   • BiGRU + Self-Attention Sequence Classifier
   • Random Forest calibration fallback             • Controlled academic & everyday sign tokens
   └────────────────────────────────┬────────────────────────────────┘
                                    ↓
                       Recognized Sign Tokens
                                    ↓
                       Natural English Translation
            (Rule-based ISL grammar + Gemini stylistic polish)
```

---

## 5. Concept Assessment Evaluation Pipeline

```
Reference Material (Text/PDF/PPT)              Student Uploaded Video (MP4)
            ↓                                                ↓
Reference Concept Extraction                   Shared Sign Recognition Service
(Nodes & Directed Relationships)                             ↓
            ↓                                  Reconstructed English Transcript
            ↓                                                ↓
            ↓                                  Student Concept Extraction
            └───────────────────────┬────────────────────────┘
                                    ↓
                     Semantic & Graph Comparison
     (SentenceTransformers Cosine Similarity + NetworkX Topological Match)
                                    ↓
              Grounded, Data-Derived Metric Scoring
         • Concept Coverage (Core & Partial understanding)
         • Relationship Accuracy (Graph edge alignment)
         • Overall Understanding Score
                                    ↓
                 Interactive Assessment Dashboard & Visuals
```

---

## 6. How to Run & Verify

### Running Django Server
```bash
python manage.py runserver 127.0.0.1:8000
```

### Running Validation Checks & Tests
```bash
python manage.py check
python manage.py test
```

### Running Training Pipelines
- **Train Alphabet Classifier**:
  ```bash
  python apps/sign_to_english/training/train_alphabet.py
  ```
- **Train Temporal Word Sequence Classifier**:
  ```bash
  python apps/sign_to_english/training/train_words.py
  ```
