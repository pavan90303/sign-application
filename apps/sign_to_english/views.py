"""
Sign to English Feature Views
=============================
Handles live camera fingerspelling (A-Z) and word sign recognition,
token debouncing, vocabulary reference drawer, and natural English sentence construction.
"""

import os
import json
import logging
import numpy as np
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required

from study_companion.sign_to_english_service import (
    get_recognition_model_singleton,
    predict_live_landmarks,
    convert_tokens_to_english,
    process_uploaded_video_file
)
from study_companion.alphabet_recognition_service import (
    predict_alphabet_letter,
    suggest_words,
    get_alphabet_service_status
)
from shared.sign_language.sign_recognition_service import SignRecognitionService

logger = logging.getLogger(__name__)


@login_required(login_url="login")
def sign_to_english_view(request):
    """
    Main Sign to English Recognition & Translation UI view.
    Renders live camera detection with MediaPipe tracking, video upload,
    token stream debouncing, and natural English conversion.
    """
    model_info = get_recognition_model_singleton()
    vocab = model_info.get("vocabulary", [])
    model_status = model_info.get('status', 'MODEL_NOT_RELIABLY_TRAINED')
    display_status = model_info.get('display_status', 'REAL ISL MODEL NOT TRAINED')
    is_trained = model_info.get('is_trained', False)
    dataset_verified = model_info.get('dataset_verified', False)

    categories = {
        "Greetings & Politeness": [s for s in vocab if s in ("HELLO", "THANK_YOU", "PLEASE", "WELCOME", "BYE")],
        "Essentials & Answers": [s for s in vocab if s in ("HELP", "WATER", "FOOD", "YES", "NO", "GOOD", "BAD", "SAFE")],
        "Pronouns & Questions": [s for s in vocab if s in ("I", "YOU", "WANT", "WHAT", "WHERE", "WHY", "HOW")],
        "Places & Daily Life": [s for s in vocab if s in ("HOME", "COLLEGE", "WORK", "LEARN", "NAME", "TIME", "DAY", "NIGHT")],
        "Campus & Roles": [s for s in vocab if s in ("STUDENT", "DOCTOR", "HOSPITAL")],
        "Science Concepts": [s for s in vocab if s in ("PLANT", "SUNLIGHT", "ENERGY")]
    }

    alpha_status = get_alphabet_service_status()

    context = {
        'page_title': 'Sign to English Recognition & Translation',
        'model_status': model_status,
        'display_status': display_status,
        'is_trained': is_trained,
        'dataset_verified': dataset_verified,
        'vocab_size': len(vocab),
        'categories': categories,
        'vocabulary': [v for v in vocab if v != "REST"],
        'alphabet_status': alpha_status,
        'alphabet_classes': alpha_status.get('labels', []),
        'model_diagnostics': {
            'pytorch_ready': model_info.get('pytorch_ready', True),
            'model_file_found': model_info.get('model_file_found', True),
            'model_loaded': model_info.get('model_loaded', True),
            'dataset_verified': dataset_verified,
            'weights_path': model_info.get('weights_path', ''),
            'architecture': model_info.get('architecture', 'ISLTemporalSequenceClassifier (BiGRU + Attention)'),
            'alphabet_architecture': alpha_status.get('architecture', 'ISLAlphabetMLP + Random Forest'),
            'alphabet_accuracy': round(alpha_status.get('test_accuracy', 0.54) * 100, 1),
            'alphabet_samples': alpha_status.get('dataset_samples', 13498)
        }
    }
    return render(request, 'sign_to_english.html', context)


@login_required(login_url="login")
def sign_to_english_live_api(request):
    """POST API for live sliding-window landmark prediction."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    frames = data.get('frames', [])
    threshold = float(data.get('threshold', 0.55))

    result = predict_live_landmarks(frames, threshold=threshold)
    return JsonResponse(result)


@login_required(login_url="login")
def sign_to_english_translate_api(request):
    """POST API for converting token arrays into fluent English."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    tokens = data.get('tokens', [])
    use_llm = data.get('use_llm', True)

    result = convert_tokens_to_english(tokens, use_llm_if_available=use_llm)
    return JsonResponse(result)


@login_required(login_url="login")
def sign_to_english_video_api(request):
    """POST API for analyzing an uploaded video file of sign gestures."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)

    video_file = request.FILES.get('video')
    if not video_file:
        return JsonResponse({'status': 'error', 'message': 'No video file uploaded.'}, status=400)

    temp_dir = os.path.join(settings.MEDIA_ROOT, 'sign_to_english_uploads')
    os.makedirs(temp_dir, exist_ok=True)

    temp_path = os.path.join(temp_dir, f"upload_{request.user.id}_{video_file.name}")
    try:
        with open(temp_path, 'wb+') as dest:
            for chunk in video_file.chunks():
                dest.write(chunk)

        threshold = float(request.POST.get('threshold', 0.45))
        result = process_uploaded_video_file(temp_path, threshold=threshold)
        return JsonResponse(result)
    except Exception as e:
        logger.exception(f"Error processing video in sign_to_english_video_api: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@login_required(login_url="login")
def sign_to_english_status_api(request):
    """GET API returning sequence model loading status and vocabulary."""
    model_info = get_recognition_model_singleton()
    return JsonResponse({
        'status': model_info.get('status', 'MODEL_READY'),
        'is_trained': model_info.get('is_trained', True),
        'vocabulary': [v for v in model_info.get('vocabulary', []) if v != "REST"],
        'architecture': model_info.get('architecture', 'ISLTemporalSequenceClassifier (BiGRU + Attention)'),
        'config': model_info.get('config', {})
    })


@login_required(login_url="login")
def sign_to_english_predict_alphabet_api(request):
    """POST API for single-frame ISL fingerspelling alphabet prediction (A-Z)."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    landmarks = data.get('landmarks', [])
    handedness = data.get('handedness', 'Right')
    threshold = float(data.get('threshold', 0.40))

    result = predict_alphabet_letter(landmarks, handedness=handedness, threshold=threshold)
    return JsonResponse(result)


@login_required(login_url="login")
def sign_to_english_suggest_word_api(request):
    """POST API for non-destructive word completions and fuzzy spelling suggestions."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    word = data.get('word', '').strip()
    suggestions = suggest_words(word)
    return JsonResponse({'status': 'ok', 'word': word, 'suggestions': suggestions})


@login_required(login_url="login")
def sign_to_english_predict_auto_api(request):
    """
    POST API for AUTO recognition mode with intelligent Decision Layer:
    Chooses between alphabet and word sequence model based on motion kinematics.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    frames = data.get('frames', [])
    landmarks = data.get('landmarks', [])
    handedness = data.get('handedness', 'Right')
    threshold = float(data.get('threshold', 0.40))

    if not frames and not landmarks:
        return JsonResponse({'status': 'WAITING_FOR_HAND', 'category': None, 'token': None, 'confidence': 0.0, 'is_reliable': False})

    motion_energy = 0.0
    has_two_hands = False
    valid_frames = []

    if frames and isinstance(frames, list):
        wrist_pts = []
        for f in frames:
            if isinstance(f, dict):
                lh = f.get('left_hand')
                rh = f.get('right_hand')
                if lh and rh:
                    has_two_hands = True
                active_h = rh if rh else lh
                if active_h and len(active_h) > 0:
                    valid_frames.append(f)
                    p0 = active_h[0]
                    wrist_pts.append([float(p0.get('x', 0)), float(p0.get('y', 0)), float(p0.get('z', 0))])

        if len(wrist_pts) >= 2:
            w_arr = np.array(wrist_pts, dtype=np.float32)
            diffs = np.linalg.norm(np.diff(w_arr, axis=0), axis=1)
            motion_energy = float(np.sum(diffs))

    latest_lm = landmarks
    if not latest_lm and frames:
        last_f = frames[-1]
        latest_lm = last_f.get('right_hand') or last_f.get('left_hand')
        if not handedness and last_f.get('left_hand') and not last_f.get('right_hand'):
            handedness = 'Left'

    alpha_res = predict_alphabet_letter(latest_lm, handedness=handedness, threshold=threshold) if latest_lm else None
    word_res = predict_live_landmarks(frames, threshold=max(0.40, threshold)) if len(frames) >= 4 else None

    if has_two_hands:
        if word_res and word_res.get("status") == "RECOGNIZED" and word_res.get("confidence", 0) >= 0.40:
            return JsonResponse({
                "status": "RECOGNIZED",
                "category": "WORD",
                "token": word_res.get("token"),
                "confidence": word_res.get("confidence"),
                "confidence_pct": int(word_res.get("confidence", 0) * 100),
                "source": "word_model",
                "is_reliable": True,
                "motion_energy": round(motion_energy, 3)
            })
        return JsonResponse({
            "status": "UNCERTAIN",
            "category": None,
            "token": None,
            "confidence": 0.0,
            "is_reliable": False,
            "message": "Two hands active; gesture not recognized as course word sign."
        })

    if motion_energy >= 0.20:
        if word_res and word_res.get("status") == "RECOGNIZED" and word_res.get("confidence", 0) >= 0.42:
            return JsonResponse({
                "status": "RECOGNIZED",
                "category": "WORD",
                "token": word_res.get("token"),
                "confidence": word_res.get("confidence"),
                "confidence_pct": int(word_res.get("confidence", 0) * 100),
                "source": "word_model",
                "is_reliable": True,
                "motion_energy": round(motion_energy, 3)
            })
        return JsonResponse({
            "status": "UNCERTAIN",
            "category": None,
            "token": None,
            "confidence": 0.0,
            "is_reliable": False,
            "message": "Dynamic motion detected, but not matched to known word sign."
        })

    if alpha_res and alpha_res.get("accepted") and alpha_res.get("status") == "SUCCESS":
        return JsonResponse({
            "status": "RECOGNIZED",
            "category": "ALPHABET",
            "token": alpha_res.get("letter"),
            "letter": alpha_res.get("letter"),
            "confidence": alpha_res.get("confidence"),
            "confidence_pct": alpha_res.get("confidence_pct"),
            "top3": alpha_res.get("top3", []),
            "source": "alphabet_model",
            "is_reliable": True,
            "motion_energy": round(motion_energy, 3)
        })

    if word_res and word_res.get("status") == "RECOGNIZED" and word_res.get("confidence", 0) >= 0.65:
        return JsonResponse({
            "status": "RECOGNIZED",
            "category": "WORD",
            "token": word_res.get("token"),
            "confidence": word_res.get("confidence"),
            "confidence_pct": int(word_res.get("confidence", 0) * 100),
            "source": "word_model",
            "is_reliable": True,
            "motion_energy": round(motion_energy, 3)
        })

    return JsonResponse({
        "status": "UNCERTAIN",
        "category": None,
        "token": None,
        "confidence": 0.0,
        "is_reliable": False
    })
