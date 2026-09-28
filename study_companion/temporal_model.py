"""
Temporal Sequence Recognition Architecture for Indian Sign Language (ISL)
==========================================================================
Provides:
- Controlled ISL Vocabulary (Academic Science Concepts & Everyday Course Signs)
- PyTorch BiGRU + Attention Sequence Classifier (ISLTemporalSequenceClassifier)
- Extraction and normalization of temporal landmark sequences
- Separation of Video Tracking Quality vs Model Recognition Confidence
- Honest model state reporting (TRAINED vs NOT_TRAINED / UNCONFIGURED)
"""

import os
import json
import logging
import numpy as np
from django.conf import settings

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

# =====================================================================
# 1. CONTROLLED ISL VOCABULARY FOR THIS PROJECT (25 Signs)
# =====================================================================
CONTROLLED_VOCABULARY = [
    # Academic & Science Concepts (Photosynthesis & Biological Processes)
    "PLANT",
    "SUNLIGHT",
    "WATER",
    "CARBON_DIOXIDE",
    "FOOD",
    "OXYGEN",
    "PROCESS",
    "ABSORB",
    "PRODUCE",
    "ENERGY",
    # Core Everyday & Course Foundations
    "HELLO",
    "THANK_YOU",
    "PLEASE",
    "YES",
    "NO",
    "HELP",
    "GOOD",
    "BAD",
    "DAY",
    "NIGHT",
    "HOME",
    "COLLEGE",
    "STUDENT",
    "DOCTOR",
    "HOSPITAL"
]

# Vocabulary index mapping
VOCAB_TO_IDX = {sign: idx for idx, sign in enumerate(CONTROLLED_VOCABULARY)}
IDX_TO_VOCAB = {idx: sign for idx, sign in enumerate(CONTROLLED_VOCABULARY)}

# Token to Semantic Concept mapping for downstream evaluation
TOKEN_TO_CONCEPT_MAP = {
    "PLANT": "plants",
    "SUNLIGHT": "sunlight",
    "WATER": "water",
    "CARBON_DIOXIDE": "carbon dioxide",
    "FOOD": "glucose",
    "OXYGEN": "oxygen",
    "ENERGY": "energy",
    "PROCESS": "photosynthesis",
    "ABSORB": "absorption",
    "PRODUCE": "synthesis",
}

SEQUENCE_LENGTH = 16   # 16 frames per sliding temporal window
FEATURE_DIM = 126      # 2 hands * 21 landmarks * 3 coordinates (x, y, z)
HIDDEN_DIM = 128
NUM_LAYERS = 2
DROPOUT = 0.3


# =====================================================================
# 2. PYTORCH TEMPORAL SEQUENCE MODEL ARCHITECTURE
# =====================================================================
class ISLTemporalSequenceClassifier(nn.Module):
    """
    Continuous ISL Sequence Recognizer using Bidirectional GRU with Temporal Attention.
    Input shape: (batch_size, sequence_length, feature_dim) [e.g. (B, 16, 126)]
    Output shape: (batch_size, num_classes) [logits]
    """
    def __init__(self, input_dim=FEATURE_DIM, hidden_dim=HIDDEN_DIM, num_classes=len(CONTROLLED_VOCABULARY), num_layers=NUM_LAYERS, dropout=DROPOUT):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.num_layers = num_layers

        # Bidirectional GRU: Captures forward and reverse temporal sign motion kinematics
        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0
        )

        # Temporal attention mechanism to weight key inflection frames
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim * 2, 64),
            nn.Tanh(),
            nn.Linear(64, 1)
        )

        # Classification Head
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        # x: (batch_size, seq_len, input_dim)
        gru_out, _ = self.gru(x)  # (batch_size, seq_len, hidden_dim * 2)

        # Temporal Attention Pooling
        attn_scores = self.attention(gru_out)  # (batch_size, seq_len, 1)
        attn_weights = torch.softmax(attn_scores, dim=1)  # (batch_size, seq_len, 1)
        context = torch.sum(attn_weights * gru_out, dim=1)  # (batch_size, hidden_dim * 2)

        # Classification logits
        logits = self.classifier(context)  # (batch_size, num_classes)
        return logits


# =====================================================================
# 3. MODEL LOADER & INTEGRITY INSPECTOR
# =====================================================================
def get_model_file_paths():
    models_dir = os.path.join(settings.BASE_DIR, 'study_companion', 'ml_models')
    return {
        "models_dir": models_dir,
        "weights_path": os.path.join(models_dir, 'isl_sequence_model.pt'),
        "config_path": os.path.join(models_dir, 'model_config.json'),
        "labels_path": os.path.join(models_dir, 'labels.json'),
        "legacy_joblib_path": os.path.join(models_dir, 'sign_classifier.joblib')
    }


def load_temporal_recognition_model():
    """
    Inspects and loads the temporal ISL sequence model.
    HONEST CONTRACT:
    - If weights file does not exist or config declares is_trained=False,
      returns status='MODEL_TRAINING_REQUIRED' with is_trained=False.
    - If file exists but deserialization or architecture check fails,
      returns status='MODEL_LOAD_FAILED' and logs the actual exception.
    - NEVER fabricates confidence values or masks untrained models.
    """
    paths = get_model_file_paths()
    weights_path = paths["weights_path"]
    config_path = paths["config_path"]
    labels_path = paths["labels_path"]

    weights_exist = os.path.exists(weights_path)
    is_trained = False
    config_info = {}

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as cf:
                config_info = json.load(cf)
                is_trained = config_info.get("is_trained", False)
        except Exception as e:
            logger.warning(f"Could not read model config: {e}")

    # Check whether trained weights are present
    if not weights_exist or not is_trained:
        return {
            "model": None,
            "status": "MODEL_TRAINING_REQUIRED",
            "is_trained": False,
            "weights_exist": weights_exist,
            "vocabulary": CONTROLLED_VOCABULARY,
            "vocabulary_size": len(CONTROLLED_VOCABULARY),
            "message": "ISL recognition architecture is configured, but no trained recognition weights are available. Add labeled ISL training data and run train_sign_recognizer.py.",
            "weights_path": weights_path,
            "architecture": "ISLTemporalSequenceClassifier (BiGRU + Attention)",
            "config": config_info
        }

    # Weights exist and config says trained -> attempt deserialization
    try:
        if not os.path.exists(labels_path):
            logger.error("Model weights exist, but labels.json mapping is missing.")
            return {
                "model": None,
                "status": "MODEL_LOAD_FAILED",
                "is_trained": False,
                "weights_exist": True,
                "vocabulary": CONTROLLED_VOCABULARY,
                "vocabulary_size": len(CONTROLLED_VOCABULARY),
                "message": "Model weights exist, but labels.json mapping is missing.",
                "weights_path": weights_path,
                "architecture": "ISLTemporalSequenceClassifier (BiGRU + Attention)",
                "config": config_info
            }

        with open(labels_path, 'r') as lf:
            labels_data = json.load(lf)
            vocab = labels_data.get("vocabulary", CONTROLLED_VOCABULARY)

        num_classes = len(vocab)
        checkpoint = torch.load(weights_path, map_location=torch.device('cpu'))

        # Checkpoint structure extraction
        if isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
        elif isinstance(checkpoint, dict):
            state_dict = checkpoint
        else:
            raise ValueError(f"Unexpected checkpoint type: {type(checkpoint)}")

        model = ISLTemporalSequenceClassifier(
            input_dim=config_info.get("feature_dim", FEATURE_DIM),
            hidden_dim=config_info.get("hidden_dim", HIDDEN_DIM),
            num_classes=num_classes,
            num_layers=config_info.get("num_layers", NUM_LAYERS),
            dropout=DROPOUT
        )
        model.load_state_dict(state_dict)
        model.eval()

        dataset_dir = os.path.join(settings.BASE_DIR, 'dataset')
        has_real_dataset = os.path.exists(dataset_dir) and any(
            os.path.isdir(os.path.join(dataset_dir, d)) for d in os.listdir(dataset_dir) if not d.startswith('.')
        )
        is_verified_trained = config_info.get("dataset_verified", False) and has_real_dataset

        status_code = "RECOGNIZER_READY" if is_verified_trained else "MODEL_NOT_RELIABLY_TRAINED"
        display_status = "RECOGNIZER READY" if is_verified_trained else "REAL ISL MODEL NOT TRAINED"

        return {
            "model": model,
            "status": status_code,
            "display_status": display_status,
            "is_trained": is_verified_trained,
            "is_reliable": is_verified_trained,
            "pytorch_ready": True,
            "model_file_found": True,
            "model_loaded": True,
            "architecture_checked": True,
            "dataset_verified": is_verified_trained,
            "weights_exist": True,
            "vocabulary": vocab,
            "vocabulary_size": num_classes,
            "message": "ISL temporal sequence model loaded and verified." if is_verified_trained else "Model weights exist on disk, but were NOT trained on a verified multi-sample dataset (dataset/ directory missing). Predictions are experimental/uncertain.",
            "weights_path": weights_path,
            "architecture": "ISLTemporalSequenceClassifier (BiGRU + Attention)",
            "config": config_info
        }

    except Exception as e:
        logger.exception(f"Failed to load ISL sequence model weights: {e}")
        return {
            "model": None,
            "status": "MODEL_LOAD_FAILED",
            "display_status": "MODEL LOAD FAILED",
            "is_trained": False,
            "is_reliable": False,
            "pytorch_ready": True,
            "model_file_found": True,
            "model_loaded": False,
            "architecture_checked": False,
            "dataset_verified": False,
            "weights_exist": True,
            "vocabulary": CONTROLLED_VOCABULARY,
            "vocabulary_size": len(CONTROLLED_VOCABULARY),
            "message": f"ISL sequence model weights could not be loaded: {str(e)}",
            "weights_path": weights_path,
            "architecture": "ISLTemporalSequenceClassifier (BiGRU + Attention)",
            "config": config_info,
            "error_details": str(e)
        }


# =====================================================================
# 4. TEMPORAL SEQUENCE PREPROCESSING & FEATURE EXTRACTION
# =====================================================================
from .isl_feature_extractor import build_temporal_sequence

def extract_temporal_sequences_from_frames(frames_data, seq_len=SEQUENCE_LENGTH, feature_dim=FEATURE_DIM):
    """
    Standardized temporal window extraction using shared ISLFeatureExtractor.
    Guarantees parity between training and live inference.
    """
    return build_temporal_sequence(frames_data, seq_len=seq_len, feature_dim=feature_dim)



# =====================================================================
# 5. INFERENCE & TEMPORAL TOKEN RECOGNITION
# =====================================================================
def run_temporal_sign_recognition(model_info, windows):
    """
    Runs sequence inference across sliding temporal windows with:
    - Input dimension compatibility check (MODEL_INPUT_SHAPE_MISMATCH)
    - Confidence thresholding & UNKNOWN class assignment
    - Temporal smoothing & duplicate suppression
    - Clean status codes: MODEL_READY, NO_RELIABLE_SIGNS, RECOGNITION_COMPLETE
    """
    if not model_info or not model_info.get("is_trained") or model_info.get("model") is None:
        status_code = model_info.get("status", "MODEL_TRAINING_REQUIRED") if model_info else "MODEL_TRAINING_REQUIRED"
        return {
            "status": status_code,
            "is_trained": False,
            "recognized_tokens": [],
            "token_details": [],
            "mean_confidence": None,
            "message": model_info.get("message", "ISL sequence recognizer is not configured. Run train_sign_recognizer.py with training data to enable recognition.") if model_info else "ISL model not configured."
        }

    if windows is None or len(windows) == 0:
        return {
            "status": "SEQUENCE_EXTRACTION_FAILED",
            "is_trained": True,
            "recognized_tokens": [],
            "token_details": [],
            "mean_confidence": None,
            "message": "No temporal landmark sequences could be extracted from video."
        }

    model = model_info["model"]

    # PART 10: Strict Feature Compatibility Validation
    if len(windows.shape) != 3 or windows.shape[2] != model.input_dim:
        logger.error(f"MODEL_INPUT_SHAPE_MISMATCH: expected feature_dim={model.input_dim}, got={windows.shape[2] if len(windows.shape) == 3 else None}")
        return {
            "status": "MODEL_INPUT_SHAPE_MISMATCH",
            "is_trained": True,
            "recognized_tokens": [],
            "token_details": [],
            "mean_confidence": None,
            "message": f"Feature dimension mismatch: model expected {model.input_dim}, but inference extracted {windows.shape[2] if len(windows.shape) == 3 else 0}."
        }

    model.eval()
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)

    tensor_in = torch.tensor(windows, dtype=torch.float32).to(device)

    with torch.no_grad():
        logits = model(tensor_in)
        probabilities = torch.softmax(logits, dim=-1).cpu().numpy()

    vocab = model_info.get("vocabulary", CONTROLLED_VOCABULARY)
    recognition_threshold = 0.50

    token_details = []
    recognized_tokens = []
    confidences = []
    unknown_count = 0
    recognized_count = 0

    for w_idx, probs in enumerate(probabilities):
        top_idx = int(np.argmax(probs))
        top_conf = float(probs[top_idx])

        # PART 13: Unknown Class & Validated Thresholding
        if top_conf < recognition_threshold:
            token_name = "UNKNOWN"
            unknown_count += 1
        else:
            token_name = vocab[top_idx] if top_idx < len(vocab) else "UNKNOWN"
            recognized_count += 1

        token_details.append({
            "window": w_idx,
            "token": token_name,
            "confidence": round(top_conf, 3),
            "is_reliable": (token_name != "UNKNOWN")
        })

        if token_name != "UNKNOWN":
            # PART 12: Duplicate suppression & temporal smoothing
            if not recognized_tokens or recognized_tokens[-1] != token_name:
                recognized_tokens.append(token_name)
                confidences.append(top_conf)

    # Check if any reliable signs were recognized
    if not recognized_tokens:
        return {
            "status": "NO_RELIABLE_SIGNS",
            "is_trained": True,
            "recognized_tokens": [],
            "token_details": token_details,
            "sequences_analyzed": len(windows),
            "recognized_count": recognized_count,
            "unknown_count": unknown_count,
            "mean_confidence": None,
            "message": "Hands tracked successfully, but no signing gestures reached the 50% recognition threshold. Try signing more distinctly with clear pauses."
        }

    mean_conf = round(float(np.mean(confidences)), 3)

    return {
        "status": "RECOGNITION_COMPLETE",
        "is_trained": True,
        "recognized_tokens": recognized_tokens,
        "token_details": token_details,
        "sequences_analyzed": len(windows),
        "recognized_count": recognized_count,
        "unknown_count": unknown_count,
        "mean_confidence": mean_conf,
        "message": f"Recognized {len(recognized_tokens)} signs across {len(windows)} temporal windows ({unknown_count} unknown sequences)."
    }
