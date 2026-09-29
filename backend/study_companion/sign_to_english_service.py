"""
Sign to English Translation and Recognition Service
===================================================
Pipeline:
Landmarks Sequence / Video -> Trained PyTorch Model -> Sign Tokens -> English Conversion
"""

import os
import json
import logging
import cv2
import numpy as np
import torch

from django.conf import settings
from .temporal_model import (
    load_temporal_recognition_model,
    SEQUENCE_LENGTH,
    FEATURE_DIM,
    extract_temporal_sequences_from_frames
)

logger = logging.getLogger(__name__)

# Cached model instance for zero-latency inference
_CACHED_MODEL_INFO = None

def get_recognition_model_singleton():
    """Returns cached temporal model or loads it if not yet loaded."""
    global _CACHED_MODEL_INFO
    if _CACHED_MODEL_INFO is None or _CACHED_MODEL_INFO.get("model") is None:
        _CACHED_MODEL_INFO = load_temporal_recognition_model()
    return _CACHED_MODEL_INFO


# =====================================================================
# 1. GRAMMAR RESTRUCTURING: SIGN TOKENS -> NATURAL ENGLISH
# =====================================================================

# Idiomatic sign phrase mappings (ISL grammar / gloss -> Fluent English)
EXACT_PHRASE_RULES = {
    # Greetings & Common Polite Expressions
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
    
    # Needs & Requests
    ("I", "WATER", "WANT"): "I want water.",
    ("I", "WANT", "WATER"): "I want water.",
    ("WATER", "WANT"): "I would like some water.",
    ("WATER", "PLEASE"): "Water, please.",
    ("I", "FOOD", "WANT"): "I want food / I want to eat.",
    ("FOOD", "WANT"): "I want to eat.",
    ("FOOD", "GOOD"): "The food is delicious.",
    ("HELP", "PLEASE"): "Please help me.",
    ("PLEASE", "HELP"): "Please help me.",
    ("I", "HELP", "WANT"): "I need help.",
    ("I", "HELP", "PLEASE"): "Please help me.",
    
    # Questions
    ("HELLO", "HOW", "YOU"): "Hello, how are you?",
    ("HOW", "YOU"): "How are you?",
    ("WHAT", "YOU", "NAME"): "What is your name?",
    ("YOU", "NAME", "WHAT"): "What is your name?",
    ("YOU", "NAME"): "What is your name?",
    ("COLLEGE", "WHERE"): "Where is the college?",
    ("WHERE", "COLLEGE"): "Where is the college?",
    ("HOME", "WHERE"): "Where is the home?",
    ("HOSPITAL", "WHERE"): "Where is the hospital?",
    ("WHERE", "HOSPITAL"): "Where is the hospital?",
    ("DOCTOR", "WHERE"): "Where is the doctor?",
    ("WHAT", "TIME"): "What time is it?",
    ("TIME", "WHAT"): "What time is it?",
    ("WHERE", "YOU"): "Where are you?",
    ("YOU", "WHERE"): "Where are you?",
    ("WHY", "YOU"): "Why are you here?",
    ("WHAT", "YOU", "WANT"): "What do you want?",
    
    # Everyday Statements & Education
    ("I", "STUDENT"): "I am a student.",
    ("I", "LEARN"): "I am learning sign language.",
    ("I", "LEARN", "STUDENT"): "I am a student learning sign language.",
    ("I", "HAPPY"): "I am happy.",
    ("I", "SAD"): "I am feeling sad.",
    ("I", "SAFE"): "I am safe.",
    ("YOU", "SAFE"): "You are safe.",
    ("WORK", "FINISH"): "The work is finished.",
    ("DAY", "GOOD"): "Good morning! Have a nice day.",
    ("NIGHT", "GOOD"): "Good night.",
    ("SAFE", "HOME"): "Safe journey home.",
    ("COLLEGE", "GO"): "I am going to college.",
    
    # Science & Academic Concepts
    ("PLANT", "SUNLIGHT", "ENERGY"): "Plants absorb sunlight to produce energy.",
    ("PLANT", "WATER", "SUNLIGHT"): "Plants require water and sunlight to grow.",
    ("SUNLIGHT", "ENERGY"): "Sunlight provides vital solar energy."
}


def rule_based_token_to_english(tokens):
    """
    Transforms an array of uppercase sign tokens into grammatically fluent English.
    Handles Subject-Object-Verb (ISL) -> Subject-Verb-Object (English).
    """
    if not tokens:
        return "No sign gestures detected."

    # Filter out REST tokens
    clean_tokens = [t.upper().strip() for t in tokens if t and t.upper().strip() not in ("REST", "UNKNOWN")]
    if not clean_tokens:
        return "Hands were detected in resting position. No active signs signed."

    # Check exact phrase tuple match
    token_tuple = tuple(clean_tokens)
    if token_tuple in EXACT_PHRASE_RULES:
        return EXACT_PHRASE_RULES[token_tuple]

    # Check sub-phrases / sliding window matches
    words = []
    i = 0
    while i < len(clean_tokens):
        matched = False
        for l in (4, 3, 2):
            if i + l <= len(clean_tokens):
                sub = tuple(clean_tokens[i:i+l])
                if sub in EXACT_PHRASE_RULES:
                    phrase = EXACT_PHRASE_RULES[sub].rstrip('.!?')
                    words.append(phrase)
                    i += l
                    matched = True
                    break
        if not matched:
            words.append(clean_tokens[i])
            i += 1

    # If already fully structured
    if len(words) == 1 and words[0] in EXACT_PHRASE_RULES.values():
        return words[0]

    # Grammar Synthesizer for arbitrary combinations
    raw_str = " ".join(words)
    raw_lower = raw_str.lower()

    # Question detection
    is_question = any(q in clean_tokens for q in ("WHAT", "WHERE", "WHY", "HOW"))

    # Word conversions
    replacements = {
        "thank_you": "thank you",
        "i": "I",
        "you": "you",
        "water": "water",
        "food": "food",
        "want": "want",
        "help": "help",
        "college": "the college",
        "hospital": "the hospital",
        "doctor": "the doctor",
        "plant": "the plant",
        "sunlight": "sunlight",
        "energy": "energy",
        "finish": "finished",
        "happy": "happy",
        "sad": "sad",
        "safe": "safe",
        "good": "good",
        "bad": "bad",
        "day": "day",
        "night": "night"
    }

    formatted_parts = []
    for token in clean_tokens:
        k = token.lower()
        formatted_parts.append(replacements.get(k, k))

    # Basic grammatical assembly
    s = " ".join(formatted_parts)
    # Fix "I happy" -> "I am happy"
    s = s.replace("I happy", "I am happy")
    s = s.replace("I sad", "I am sad")
    s = s.replace("I safe", "I am safe")
    s = s.replace("you safe", "you are safe")
    s = s.replace("I student", "I am a student")
    s = s.replace("I learn", "I am learning")

    # Capitalize first letter
    sentence = s[0].upper() + s[1:] if len(s) > 1 else s.upper()

    # Punctuate
    if is_question:
        if not sentence.endswith("?"):
            sentence += "?"
    else:
        if not sentence.endswith((".", "!", "?")):
            sentence += "."

    return sentence


def convert_tokens_to_english(tokens, use_llm_if_available=True):
    """
    Translates sign tokens into natural readable English.
    Uses rule-based grammar restructuring, and optionally enhances with Gemini if API key is present.
    """
    if not tokens:
        return {
            "english": "No signs detected.",
            "tokens": [],
            "source": "rule_based"
        }

    clean_tokens = [t.upper().strip() for t in tokens if t and t.upper().strip() not in ("REST", "UNKNOWN")]
    if not clean_tokens:
        return {
            "english": "Hands were at rest. No active sign gestures recognized.",
            "tokens": [],
            "source": "rule_based"
        }

    rule_english = rule_based_token_to_english(clean_tokens)

    # Optional Gemini LLM enhancement if key exists
    gemini_key = getattr(settings, 'GEMINI_API_KEY', None) or os.getenv('GEMINI_API_KEY')
    if use_llm_if_available and gemini_key and len(clean_tokens) >= 2:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = (
                f"You are an expert Indian Sign Language (ISL) translator. "
                f"Convert these raw recognized sign tokens into a single, natural, fluent English sentence: "
                f"{' + '.join(clean_tokens)}. "
                f"Return ONLY the plain English sentence without quotation marks or explanations."
            )
            response = model.generate_content(prompt, request_options={"timeout": 3.0})
            if response and response.text:
                refined = response.text.strip().replace('"', '')
                if len(refined) > 2:
                    return {
                        "english": refined,
                        "tokens": clean_tokens,
                        "source": "gemini_llm",
                        "rule_fallback": rule_english
                    }
        except Exception as e:
            logger.debug(f"Gemini LLM token enhancement skipped: {e}")

    return {
        "english": rule_english,
        "tokens": clean_tokens,
        "source": "rule_based"
    }


# =====================================================================
# 2. LIVE CAMERA FRAME PREDICTOR & QUALITY GATE
# =====================================================================
from .isl_feature_extractor import (
    build_temporal_sequence,
    validate_model_input_shape,
    TOTAL_FEATURE_DIM,
    SEQUENCE_LENGTH
)

def predict_live_landmarks(frames_buffer, threshold=0.55):
    """
    Quality-gated inference on sliding frames buffer from browser camera.
    Enforces Phase 10 (Quality Gate) & Phase 12 (Confidence & Uncertainty Handling):
    - Rejects empty / handless frames -> WAITING_FOR_HANDS
    - Rejects low-confidence transition noise -> UNCERTAIN (never returns token)
    - Rejects rest baseline -> NEUTRAL_REST
    - Only returns token when confidence >= threshold and reliable.
    """
    model_info = get_recognition_model_singleton()
    if not model_info or model_info.get("model") is None:
        return {
            "status": "MODEL_NOT_READY",
            "display_text": "Model not loaded",
            "helper": "Please ensure the model weights are loaded.",
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
            "helper": "Position your hand within the camera frame.",
            "token": None,
            "confidence": 0.0,
            "is_reliable": False,
            "is_rest": True,
            "top3": [],
            "state": "WAITING_FOR_HANDS"
        }

    # Quality Gate: Check if any valid landmarks exist in buffer
    has_any_hands = False
    for f in frames_buffer:
        if isinstance(f, dict):
            if f.get('left_hand') or f.get('right_hand') or f.get('landmarks'):
                has_any_hands = True
                break

    if not has_any_hands:
        return {
            "status": "WAITING_FOR_HANDS",
            "display_text": "Waiting for hands...",
            "helper": "Position your hand within the camera frame.",
            "token": None,
            "confidence": 0.0,
            "is_reliable": False,
            "is_rest": True,
            "top3": [],
            "state": "WAITING_FOR_HANDS"
        }

    # Build standardized temporal window using shared feature extractor
    windows = build_temporal_sequence(frames_buffer, seq_len=SEQUENCE_LENGTH, feature_dim=expected_dim)
    if windows is None or len(windows) == 0:
        return {
            "status": "BUFFER_TOO_SHORT",
            "display_text": "Buffering motion...",
            "helper": "Hold sign steadily.",
            "token": None,
            "confidence": 0.0,
            "is_reliable": False,
            "top3": [],
            "state": "COLLECTING"
        }

    # Evaluate the most recent sliding window
    last_window = windows[-1:] # shape (1, 16, expected_dim)

    # Phase 7: Strict input shape validation
    valid_shape, shape_err = validate_model_input_shape(last_window, expected_dim=expected_dim, expected_len=SEQUENCE_LENGTH)
    if not valid_shape:
        logger.error(f"MODEL_INPUT_SHAPE_MISMATCH: {shape_err}")
        return {
            "status": "MODEL_INPUT_MISMATCH",
            "display_text": "Input shape mismatch",
            "helper": str(shape_err),
            "token": None,
            "confidence": 0.0,
            "is_reliable": False,
            "top3": [],
            "state": "ERROR"
        }

    tensor_in = torch.tensor(last_window, dtype=torch.float32)

    model.eval()
    with torch.no_grad():
        logits = model(tensor_in)
        probs = torch.softmax(logits, dim=-1).squeeze(0).numpy()

    top_idx = int(np.argmax(probs))
    top_conf = float(probs[top_idx])
    token_name = vocab[top_idx] if top_idx < len(vocab) else "REST"

    # Top 3 predictions for diagnostics panel ONLY
    top3_indices = np.argsort(probs)[-3:][::-1]
    top3 = [
        {"token": vocab[i] if i < len(vocab) else "REST", "confidence": round(float(probs[i]), 3)}
        for i in top3_indices
    ]

    # Neutral / Rest state
    if token_name == "REST":
        return {
            "status": "NEUTRAL_REST",
            "display_text": "Hands at rest position",
            "helper": "Ready for next sign.",
            "token": None, # Never register REST as a sign token
            "candidate_token": "REST",
            "confidence": round(top_conf, 3),
            "is_reliable": False,
            "is_rest": True,
            "top3": top3,
            "state": "NEUTRAL_REST"
        }

    # Phase 12: Confidence filter & Uncertainty handling
    if top_conf < threshold:
        return {
            "status": "UNCERTAIN",
            "display_text": "Sign not confidently recognized",
            "helper": "Please repeat the sign clearly.",
            "token": None, # DO NOT emit uncertain token
            "candidate_token": token_name,
            "confidence": round(top_conf, 3),
            "is_reliable": False,
            "is_rest": False,
            "top3": top3,
            "state": "UNCERTAIN"
        }

    # High-confidence genuine sign recognition
    return {
        "status": "RECOGNIZED",
        "display_text": token_name,
        "helper": f"Registered with {int(top_conf * 100)}% confidence.",
        "token": token_name,
        "candidate_token": token_name,
        "confidence": round(top_conf, 3),
        "is_reliable": True,
        "is_rest": False,
        "top3": top3,
        "state": "RECOGNIZED"
    }



# =====================================================================
# 3. VIDEO UPLOAD PROCESSOR (OpenCV + Landmark Extraction + PyTorch)
# =====================================================================

def process_uploaded_video_file(video_path, threshold=0.55):
    """
    Extracts landmark frames from an uploaded video file using OpenCV,
    runs temporal PyTorch sequence inference across all sliding windows,
    debounces recognized sign tokens, and converts them to natural English.
    """
    if not os.path.exists(video_path):
        return {
            "status": "FILE_NOT_FOUND",
            "error": "Uploaded video file not found."
        }

    model_info = get_recognition_model_singleton()
    if not model_info or model_info.get("model") is None:
        return {
            "status": "MODEL_NOT_READY",
            "error": "ISL recognition model is not loaded."
        }


    model = model_info["model"]
    vocab = model_info.get("vocabulary", [])

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {
            "status": "INVALID_VIDEO",
            "error": "Could not open video file."
        }

    raw_frames_data = []
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    frame_idx = 0
    while cap.isOpened() and frame_idx < 600: # Limit to 600 frames (~20s)
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        # Extract hand contours / skin motion proxy landmarks
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([0, 20, 70], dtype=np.uint8), np.array([20, 255, 255], dtype=np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        frame_landmarks = []
        if contours:
            # Find largest 1 or 2 contours for 2 hands
            sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)[:2]
            for c in sorted_contours:
                if cv2.contourArea(c) > (w * h * 0.003):
                    M = cv2.moments(c)
                    if M["m00"] > 0:
                        cx = (M["m10"] / M["m00"]) / w
                        cy = (M["m01"] / M["m00"]) / h
                        for k in range(21):
                            frame_landmarks.append({
                                'x': cx + float(np.sin(k * 0.3) * 0.04),
                                'y': cy + float(np.cos(k * 0.3) * 0.04),
                                'z': 0.0
                            })

        # Pad to at least 21 landmarks if at least one hand found
        if frame_landmarks:
            raw_frames_data.append({'landmarks': frame_landmarks})
        else:
            raw_frames_data.append({'landmarks': [{'x': 0.5, 'y': 0.8, 'z': 0.0} for _ in range(21)]})

    cap.release()

    if len(raw_frames_data) < 8:
        return {
            "status": "INSUFFICIENT_FRAMES",
            "error": "Video is too short or no signing gestures were detected."
        }

    # Extract temporal windows using shared feature extractor
    feature_dim = getattr(model, 'input_dim', FEATURE_DIM)
    windows = extract_temporal_sequences_from_frames(raw_frames_data, seq_len=SEQUENCE_LENGTH, feature_dim=feature_dim)

    if windows is None or len(windows) == 0:
        return {
            "status": "NO_SEQUENCES",
            "error": "Could not extract temporal sequences from video."
        }

    # Model inference
    model.eval()
    tensor_in = torch.tensor(windows, dtype=torch.float32)
    with torch.no_grad():
        logits = model(tensor_in)
        probabilities = torch.softmax(logits, dim=-1).numpy()

    timeline = []
    debounced_tokens = []
    confidences = []

    last_token = None

    for w_idx, probs in enumerate(probabilities):
        top_idx = int(np.argmax(probs))
        top_conf = float(probs[top_idx])
        token_name = vocab[top_idx] if top_idx < len(vocab) else "REST"

        timestamp_sec = round((w_idx * (SEQUENCE_LENGTH // 2)) / fps, 2)

        timeline.append({
            "window_index": w_idx,
            "timestamp": timestamp_sec,
            "token": token_name,
            "confidence": round(top_conf, 3),
            "is_reliable": (top_conf >= threshold and token_name != "REST")
        })

        if top_conf >= threshold and token_name != "REST":
            # Debounce repeated tokens
            if last_token != token_name:
                debounced_tokens.append(token_name)
                confidences.append(top_conf)
                last_token = token_name
        else:
            if token_name == "REST":
                last_token = None # Allow repeating same sign after rest

    # Convert to English
    translation_result = convert_tokens_to_english(debounced_tokens)
    mean_conf = round(float(np.mean(confidences)), 3) if confidences else 0.0

    return {
        "status": "SUCCESS",
        "recognized_tokens": debounced_tokens,
        "english_translation": translation_result["english"],
        "translation_source": translation_result.get("source", "rule_based"),
        "mean_confidence": mean_conf,
        "frames_analyzed": len(raw_frames_data),
        "windows_analyzed": len(windows),
        "timeline": timeline[:50] # return first 50 sample points
    }
