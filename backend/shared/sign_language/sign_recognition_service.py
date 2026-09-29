"""
Unified Sign Recognition Service
================================
Authoritative, shared ISL recognition service for SignAI Pro.
Reused by both Sign-to-English and Concept Assessment features.

Pipeline:
Video / Camera Frames
        ↓
    MediaPipe
        ↓
    Landmarks
        ↓
  Preprocessing (86-dim / 126-dim canonical geometry)
        ↓
Trained Recognition Models (PyTorch Alphabet MLP + BiGRU Temporal Sequence)
        ↓
Recognized ISL Tokens
        ↓
English Translation & Concept Alignment
"""

import os
import json
import logging
import cv2
import numpy as np
import torch
import torch.nn as nn
from django.conf import settings

from .isl_preprocessing import extract_isl_features, parse_raw_landmarks, FEATURE_DIM as ALPHABET_FEATURE_DIM
from .temporal_model import (
    load_temporal_recognition_model,
    SEQUENCE_LENGTH,
    FEATURE_DIM as TEMPORAL_FEATURE_DIM,
    ISLTemporalSequenceClassifier
)
from .isl_feature_extractor import (
    build_temporal_sequence,
    validate_model_input_shape,
    TOTAL_FEATURE_DIM
)
from .vocabulary import CONTROLLED_VOCABULARY, WORD_SUGGESTION_VOCABULARY

logger = logging.getLogger(__name__)

# Singletons
_CACHED_TEMPORAL_MODEL = None
_CACHED_ALPHABET_MODEL = None


def get_temporal_model_singleton():
    """Returns cached temporal model info or loads it."""
    global _CACHED_TEMPORAL_MODEL
    if _CACHED_TEMPORAL_MODEL is None or _CACHED_TEMPORAL_MODEL.get("model") is None:
        _CACHED_TEMPORAL_MODEL = load_temporal_recognition_model()
    return _CACHED_TEMPORAL_MODEL


class ISLAlphabetMLP(nn.Module):
    """PyTorch Classifier for 86-dim ISL Handshape Features -> 26 classes (A-Z)."""
    def __init__(self, input_dim=86, num_classes=26):
        super(ISLAlphabetMLP, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(0.1),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.LeakyReLU(0.1),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.LeakyReLU(0.1),
            nn.Dropout(0.10),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        return self.net(x)


def get_alphabet_model_singleton():
    """Returns cached alphabet model info."""
    global _CACHED_ALPHABET_MODEL
    if _CACHED_ALPHABET_MODEL is not None:
        return _CACHED_ALPHABET_MODEL

    try:
        base_dir = settings.BASE_DIR
    except Exception:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate_paths = [
        os.path.join(base_dir, 'models', 'sign_to_english', 'alphabet'),
        os.path.join(base_dir, 'study_companion', 'ml_models'),
    ]

    model_dir = None
    for cp in candidate_paths:
        if os.path.exists(os.path.join(cp, 'isl_alphabet_model.pt')):
            model_dir = cp
            break

    if not model_dir:
        logger.warning("ISL Alphabet model not found in candidates.")
        return None

    try:
        labels_path = os.path.join(model_dir, 'alphabet_labels.json')
        labels = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        if os.path.exists(labels_path):
            with open(labels_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    labels = data.get('labels', labels)
                elif isinstance(data, list):
                    labels = data

        model = ISLAlphabetMLP(input_dim=86, num_classes=len(labels))
        weights_path = os.path.join(model_dir, 'isl_alphabet_model.pt')
        ckpt = torch.load(weights_path, map_location='cpu')
        if isinstance(ckpt, dict) and 'model_state_dict' in ckpt:
            model.load_state_dict(ckpt['model_state_dict'])
        else:
            model.load_state_dict(ckpt)
        model.eval()

        _CACHED_ALPHABET_MODEL = {
            "model": model,
            "labels": labels,
            "num_classes": len(labels)
        }
        return _CACHED_ALPHABET_MODEL
    except Exception as e:
        logger.error(f"Failed to load ISL Alphabet model: {e}")
        return None


# Idiomatic sign phrase mappings
EXACT_PHRASE_RULES = {
    ("HELLO",): "Hello!",
    ("BYE",): "Goodbye! Have a great day.",
    ("WELCOME",): "You are welcome.",
    ("THANK_YOU",): "Thank you very much.",
    ("PLEASE",): "Please.",
    ("YES",): "Yes, that is correct.",
    ("NO",): "No.",
    ("GOOD",): "Good!",
    ("BAD",): "That is bad / wrong.",
    ("SAFE",): "It is safe.",
    ("I", "WATER", "WANT"): "I want water.",
    ("I", "WANT", "WATER"): "I want water.",
    ("WATER", "WANT"): "I would like some water.",
    ("WATER", "PLEASE"): "Water, please.",
    ("I", "FOOD", "WANT"): "I want food / I want to eat.",
    ("FOOD", "WANT"): "I want to eat.",
    ("I", "HELP", "WANT"): "I need help.",
    ("YOU", "HELP", "PLEASE"): "Could you please help me?",
    ("HELP", "PLEASE"): "Please help me.",
    ("WHAT", "NAME"): "What is your name?",
    ("YOU", "NAME", "WHAT"): "What is your name?",
    ("I", "LEARN", "SIGN"): "I am learning sign language.",
    ("PLANT", "SUNLIGHT", "WATER"): "Plants absorb sunlight and water to produce energy.",
    ("PLANT", "WATER", "SUNLIGHT"): "Plants absorb sunlight and water to produce food.",
    ("PLANT", "SUNLIGHT", "WATER", "FOOD"): "Plants use sunlight and water to create food through photosynthesis.",
    ("PLANT", "SUNLIGHT", "WATER", "ENERGY"): "Plants capture sunlight and absorb water to generate vital biological energy.",
    ("SUNLIGHT", "WATER", "FOOD", "OXYGEN"): "With sunlight and water, plants synthesize food and release oxygen into the atmosphere.",
    ("PLANT", "CARBON_DIOXIDE", "WATER", "FOOD", "OXYGEN"): "Plants take in carbon dioxide and water to produce glucose and release oxygen.",
}


def rule_based_token_to_english(tokens):
    """Converts sign tokens to natural English sentence."""
    if not tokens:
        return ""
    upper_tokens = tuple(t.upper().strip() for t in tokens if t and t.upper().strip() not in ("REST", "UNKNOWN"))
    if not upper_tokens:
        return ""
    if upper_tokens in EXACT_PHRASE_RULES:
        return EXACT_PHRASE_RULES[upper_tokens]

    formatted_words = []
    for t in upper_tokens:
        w = t.replace("_", " ").lower()
        if w == "i":
            formatted_words.append("I")
        else:
            formatted_words.append(w)

    sentence = " ".join(formatted_words).capitalize()
    if upper_tokens and upper_tokens[-1] in ("WHAT", "WHERE", "WHY", "HOW", "WHEN"):
        if not sentence.endswith("?"):
            sentence += "?"
    else:
        if not sentence.endswith((".", "!", "?")):
            sentence += "."
    return sentence


def convert_tokens_to_english(tokens, use_llm_if_available=True):
    """Translates sign tokens into natural readable English."""
    if not tokens:
        return {"english": "No signs detected.", "tokens": [], "source": "rule_based"}

    clean_tokens = [t.upper().strip() for t in tokens if t and t.upper().strip() not in ("REST", "UNKNOWN")]
    if not clean_tokens:
        return {"english": "Hands were at rest. No active sign gestures recognized.", "tokens": [], "source": "rule_based"}

    rule_english = rule_based_token_to_english(clean_tokens)

    from shared.ai.gemini_service import call_gemini_model
    if use_llm_if_available and len(clean_tokens) >= 2:
        prompt = (
            f"You are an expert Indian Sign Language (ISL) translator. "
            f"Convert these raw recognized sign tokens into a single, natural, fluent English sentence: "
            f"{' + '.join(clean_tokens)}. "
            f"Return ONLY the plain English sentence without quotation marks or explanations."
        )
        gemini_result = call_gemini_model(prompt)
        if gemini_result:
            refined = gemini_result.strip().replace('"', '')
            if len(refined) > 2:
                return {
                    "english": refined,
                    "tokens": clean_tokens,
                    "source": "gemini_llm",
                    "rule_fallback": rule_english
                }

    return {"english": rule_english, "tokens": clean_tokens, "source": "rule_based"}


class SignRecognitionService:
    """
    Centralized Sign Recognition Service interface.
    Exposes high-level methods for both single frame and temporal video sign recognition.
    """

    @classmethod
    def get_status(cls):
        """Returns readiness status of both Alphabet and Sequence models."""
        alphabet_info = get_alphabet_model_singleton()
        temporal_info = get_temporal_model_singleton()
        return {
            "alphabet_model_ready": alphabet_info is not None,
            "temporal_model_ready": temporal_info is not None and temporal_info.get("model") is not None,
            "vocabulary_size": len(temporal_info.get("vocabulary", [])) if temporal_info else 0
        }

    @classmethod
    def predict_alphabet(cls, landmarks, handedness='Right'):
        """Predicts ISL alphabet letter (A-Z) from single-frame MediaPipe hand landmarks."""
        model_info = get_alphabet_model_singleton()
        if not model_info:
            return {"letter": None, "confidence": 0.0, "status": "MODEL_NOT_READY", "top3": []}

        features = extract_isl_features(landmarks, handedness=handedness)
        tensor_in = torch.tensor(features, dtype=torch.float32).unsqueeze(0)

        model = model_info["model"]
        labels = model_info["labels"]

        with torch.no_grad():
            logits = model(tensor_in)
            probs = torch.softmax(logits, dim=1).numpy()[0]

        top_indices = np.argsort(probs)[::-1][:3]
        best_idx = top_indices[0]
        confidence = float(probs[best_idx])
        letter = labels[best_idx]

        top3 = [{"letter": labels[i], "confidence": round(float(probs[i]), 3)} for i in top_indices]

        return {
            "letter": letter,
            "confidence": round(confidence, 4),
            "status": "DETECTED" if confidence >= 0.45 else "UNCERTAIN",
            "top3": top3
        }

    @classmethod
    def predict_sequence(cls, frames_buffer, threshold=0.55):
        """
        Quality-gated prediction on sliding temporal window from browser webcam.
        Rejects noise, empty frames, and rest states.
        """
        model_info = get_temporal_model_singleton()
        if not model_info or model_info.get("model") is None:
            return {
                "status": "MODEL_NOT_READY",
                "display_text": "Model not loaded",
                "token": None,
                "confidence": 0.0,
                "is_reliable": False,
                "top3": [],
                "state": "ERROR"
            }

        model = model_info["model"]
        vocab = model_info.get("vocabulary", [])
        expected_dim = getattr(model, 'input_dim', TOTAL_FEATURE_DIM)

        if not frames_buffer or len(frames_buffer) == 0:
            return {
                "status": "WAITING_FOR_HANDS",
                "display_text": "Waiting for hands...",
                "token": None,
                "confidence": 0.0,
                "is_reliable": False,
                "is_rest": True,
                "top3": [],
                "state": "WAITING_FOR_HANDS"
            }

        has_any_hands = any(
            f.get('left_hand') or f.get('right_hand') or f.get('landmarks')
            for f in frames_buffer if isinstance(f, dict)
        )
        if not has_any_hands:
            return {
                "status": "WAITING_FOR_HANDS",
                "display_text": "Waiting for hands...",
                "token": None,
                "confidence": 0.0,
                "is_reliable": False,
                "is_rest": True,
                "top3": [],
                "state": "WAITING_FOR_HANDS"
            }

        windows = build_temporal_sequence(frames_buffer, seq_len=SEQUENCE_LENGTH, feature_dim=expected_dim)
        if windows is None or len(windows) == 0:
            return {
                "status": "BUFFER_TOO_SHORT",
                "display_text": "Buffering motion...",
                "token": None,
                "confidence": 0.0,
                "is_reliable": False,
                "top3": [],
                "state": "COLLECTING"
            }

        last_window = windows[-1:]  # (1, 16, expected_dim)
        inp = torch.tensor(last_window, dtype=torch.float32)

        with torch.no_grad():
            outputs = model(inp)
            probs = torch.softmax(outputs, dim=1).numpy()[0]

        top_indices = np.argsort(probs)[::-1][:3]
        best_idx = top_indices[0]
        confidence = float(probs[best_idx])
        token = vocab[best_idx] if best_idx < len(vocab) else "UNKNOWN"

        top3 = [{"sign": vocab[i] if i < len(vocab) else "UNKNOWN", "confidence": round(float(probs[i]), 3)} for i in top_indices]

        is_rest = token == "REST"
        is_reliable = (confidence >= threshold) and not is_rest

        return {
            "status": "DETECTED" if is_reliable else ("NEUTRAL_REST" if is_rest else "UNCERTAIN"),
            "display_text": token.replace("_", " ") if is_reliable else ("Resting..." if is_rest else "Analyzing..."),
            "token": token if is_reliable else None,
            "confidence": round(confidence, 4),
            "is_reliable": is_reliable,
            "is_rest": is_rest,
            "top3": top3,
            "state": "CONFIDENT" if is_reliable else "COLLECTING"
        }

    @classmethod
    def process_video_file(cls, video_path, min_confidence=0.40):
        """
        Processes an entire MP4 video file through MediaPipe and the PyTorch sequence model.
        Returns recognized tokens and reconstructed English transcript.
        Used by both Sign-to-English video upload and Concept Assessment.
        """
        from study_companion.sign_to_english_service import process_video_for_signs
        return process_video_for_signs(video_path, min_confidence=min_confidence)

    @classmethod
    def tokens_to_english(cls, tokens, use_llm_if_available=True):
        """Translates token list to fluent English."""
        return convert_tokens_to_english(tokens, use_llm_if_available=use_llm_if_available)

    @classmethod
    def suggest_words(cls, current_word, top_n=5):
        """Fuzzy autocomplete / dictionary word suggestions from fingerspelled letters."""
        if not current_word or len(current_word) == 0:
            return []
        cw = current_word.upper().strip()
        matches = [w for w in WORD_SUGGESTION_VOCABULARY if w.startswith(cw)]
        if len(matches) < top_n:
            import difflib
            fuzzy = difflib.get_close_matches(cw, WORD_SUGGESTION_VOCABULARY, n=top_n - len(matches), cutoff=0.6)
            for f in fuzzy:
                if f not in matches:
                    matches.append(f)
        return matches[:top_n]
