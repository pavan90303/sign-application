"""
Adapter for the verified trained ISL recognition model in the repository:
'study_companion/ml_models/sign_classifier.joblib'.

Provides real inference on video frames and sliding temporal segments,
with honest classification of unknown / unsupported signs.
"""
import os
import joblib
import numpy as np
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class RepositoryISLAdapter:
    ENGINE_NAME = "RepositoryISLRecognizer"
    MODEL_FILENAME = "sign_classifier.joblib"

    def __init__(self):
        self.model_path = os.path.join(settings.BASE_DIR, 'study_companion', 'ml_models', self.MODEL_FILENAME)
        self.model = None
        self.classes = []
        self.n_features = 170
        self.is_loaded = False
        self.status = "UNCHECKED"
        self._load_model()

    def _load_model(self):
        if not os.path.exists(self.model_path):
            self.is_loaded = False
            self.status = "PRETRAINED_MODEL_NOT_AVAILABLE"
            return

        try:
            self.model = joblib.load(self.model_path)
            self.classes = list(getattr(self.model, 'classes_', []))
            self.n_features = int(getattr(self.model, 'n_features_in_', 170))
            self.is_loaded = True
            self.status = "PRETRAINED_ISL_MODEL_READY"
        except Exception as e:
            logger.error(f"[RepositoryISLAdapter] Failed to load {self.model_path}: {e}")
            self.model = None
            self.is_loaded = False
            self.status = "MODEL_LOAD_FAILED"

    def get_diagnostics(self) -> dict:
        return {
            "engine": self.ENGINE_NAME,
            "model": f"RandomForestClassifier({len(self.classes)}_ISL_classes)",
            "model_path": self.model_path,
            "is_loaded": self.is_loaded,
            "status": self.status,
            "number_of_labels": len(self.classes),
            "supported_vocabulary": [c.upper() for c in self.classes],
            "supports_continuous": False,
            "continuous_warning": "Model trained on 29 isolated ISL signs and alphabet gestures. Continuous signing for academic concepts is segment-analyzed; gestures outside the 29 classes will be marked UNKNOWN."
        }

    def recognize_frames(self, frames_data: list, fps: float = 30.0) -> dict:
        """
        Segments frame landmark stream, runs real inference using RandomForest model,
        and returns structured token predictions without fabrication.
        """
        if not self.is_loaded or self.model is None:
            return {
                "success": False,
                "engine": self.ENGINE_NAME,
                "model": "None",
                "status": self.status,
                "tokens": [],
                "recognized_signs": [],
                "unknown_segments": 0,
                "segments_analyzed": 0,
                "confidence": None,
                "supported_vocabulary": []
            }

        from study_companion.sign_recognition import extract_sequence_features

        # Filter frames containing hand landmarks
        valid_frames = []
        for f in frames_data:
            lms = f if isinstance(f, list) else f.get('landmarks', [])
            if lms and len(lms) >= 21:
                valid_frames.append(f)

        if len(valid_frames) < 4:
            return {
                "success": True,
                "engine": self.ENGINE_NAME,
                "model": f"RandomForestClassifier({len(self.classes)}_ISL_classes)",
                "status": "NO_RELIABLE_SIGNS",
                "message": "Insufficient hand landmark frames detected for reliable recognition.",
                "tokens": [],
                "recognized_signs": [],
                "unknown_segments": 1,
                "segments_analyzed": 1,
                "confidence": None,
                "supported_vocabulary": [c.upper() for c in self.classes]
            }

        # Divide into sliding windows of 12-16 frames
        window_size = 14
        step_size = 8
        windows = []
        timestamps = []

        for start_idx in range(0, len(valid_frames) - 3, step_size):
            end_idx = min(start_idx + window_size, len(valid_frames))
            chunk = valid_frames[start_idx:end_idx]
            if len(chunk) >= 4:
                windows.append(chunk)
                t_start = round(start_idx / max(fps, 1.0), 2)
                t_end = round(end_idx / max(fps, 1.0), 2)
                timestamps.append((t_start, t_end))

        if not windows:
            windows = [valid_frames]
            timestamps = [(0.0, round(len(valid_frames) / max(fps, 1.0), 2))]

        tokens = []
        recognized_signs = []
        unknown_segments = 0
        confidences = []

        CONFIDENCE_THRESHOLD = 0.40

        for idx, (win, (t_start, t_end)) in enumerate(zip(windows, timestamps)):
            feat_vec, _ = extract_sequence_features(win)
            # Ensure correct feature dimension
            if len(feat_vec) < self.n_features:
                feat_vec = np.pad(feat_vec, (0, self.n_features - len(feat_vec)), mode='constant')
            elif len(feat_vec) > self.n_features:
                feat_vec = feat_vec[:self.n_features]

            probs = self.model.predict_proba([feat_vec])[0]
            top_idx = int(np.argmax(probs))
            top_prob = float(probs[top_idx])
            top_class = self.classes[top_idx].upper()

            if top_prob >= CONFIDENCE_THRESHOLD:
                # Suppress immediate duplicate consecutive predictions within 1 second
                if not tokens or tokens[-1]["label"] != top_class or (t_start - tokens[-1]["end"]) > 1.2:
                    token_obj = {
                        "label": top_class,
                        "confidence": round(top_prob, 3),
                        "start": t_start,
                        "end": t_end
                    }
                    tokens.append(token_obj)
                    recognized_signs.append(top_class)
                    confidences.append(top_prob)
            else:
                unknown_segments += 1

        mean_conf = round(float(np.mean(confidences)), 3) if confidences else None

        # Determine pipeline status
        if tokens:
            final_status = "RECOGNITION_COMPLETE"
        elif unknown_segments > 0:
            final_status = "NO_RELIABLE_SIGNS"
        else:
            final_status = "NO_RELIABLE_SIGNS"

        return {
            "success": True,
            "engine": self.ENGINE_NAME,
            "model": f"RandomForestClassifier({len(self.classes)}_ISL_classes)",
            "status": final_status,
            "tokens": tokens,
            "recognized_signs": recognized_signs,
            "unknown_segments": unknown_segments,
            "segments_analyzed": len(windows),
            "confidence": mean_conf,
            "supported_vocabulary": [c.upper() for c in self.classes]
        }
