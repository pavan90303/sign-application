"""
Unified ISL Feature Extraction & Normalization Module
====================================================
Shared single source of truth for BOTH training and inference.
Guarantees exact parity in:
- Landmark ordering
- Dedicated Left Hand (63) and Right Hand (63) slots (handedness-aware)
- Upper body Pose landmarks (18)
- Wrist-relative translation and palm-scale normalization
- Shoulder-relative pose normalization
- Sequence length and tensor shape validation
"""

import numpy as np
import torch
import logging

logger = logging.getLogger(__name__)

# Standard sequence and feature dimensions
SEQUENCE_LENGTH = 16   # 16 frames per sliding temporal window
LEFT_HAND_DIM = 63     # 21 landmarks * 3 coords (x, y, z)
RIGHT_HAND_DIM = 63    # 21 landmarks * 3 coords (x, y, z)
POSE_DIM = 18          # 6 landmarks * 3 coords: Nose(0), L_Shoulder(11), R_Shoulder(12), L_Elbow(13), R_Elbow(14), Midpoint
TOTAL_FEATURE_DIM = 144  # 63 + 63 + 18 = 144 dimensions

# Key pose landmark indices from MediaPipe Pose (33 total)
# 0: Nose, 11: Left Shoulder, 12: Right Shoulder, 13: Left Elbow, 14: Right Elbow
KEY_POSE_INDICES = [0, 11, 12, 13, 14]


def normalize_hand_landmarks(landmarks):
    """
    Normalizes a single hand's 21 3D landmarks (x, y, z):
    1. Translates wrist (index 0) to local origin (0, 0, 0).
    2. Scales by distance between wrist (0) and middle finger MCP (9).
       Fallback to index MCP (5) or 1.0 if palm scale is degenerate.
    Returns: 63-dimensional numpy float32 vector.
    """
    if landmarks is None or len(landmarks) < 21:
        return np.zeros(LEFT_HAND_DIM, dtype=np.float32)

    pts = np.zeros((21, 3), dtype=np.float32)
    for i in range(21):
        p = landmarks[i]
        if isinstance(p, dict):
            pts[i] = [float(p.get('x', 0.0)), float(p.get('y', 0.0)), float(p.get('z', 0.0))]
        elif isinstance(p, (list, tuple)) and len(p) >= 3:
            pts[i] = [float(p[0]), float(p[1]), float(p[2])]
        elif isinstance(p, (list, tuple)) and len(p) == 2:
            pts[i] = [float(p[0]), float(p[1]), 0.0]

    # Wrist is origin
    wrist = pts[0].copy()
    centered = pts - wrist

    # Scale normalization by distance between wrist (0) and middle MCP (9)
    palm_scale = np.linalg.norm(centered[9])
    if palm_scale < 1e-4:
        palm_scale = np.linalg.norm(centered[5])
        if palm_scale < 1e-4:
            palm_scale = 1.0

    normalized = centered / palm_scale
    return normalized.flatten().astype(np.float32)


def normalize_pose_landmarks(pose_landmarks):
    """
    Normalizes upper-body pose landmarks:
    Uses midpoint between Left Shoulder (11) and Right Shoulder (12) as origin.
    Scales by shoulder width distance.
    Returns: 18-dimensional numpy float32 vector (6 keypoints * 3).
    """
    if pose_landmarks is None or len(pose_landmarks) < 15:
        return np.zeros(POSE_DIM, dtype=np.float32)

    pts = {}
    for idx in KEY_POSE_INDICES:
        if idx < len(pose_landmarks):
            p = pose_landmarks[idx]
            if isinstance(p, dict):
                pts[idx] = np.array([float(p.get('x', 0.0)), float(p.get('y', 0.0)), float(p.get('z', 0.0))], dtype=np.float32)
            elif isinstance(p, (list, tuple)) and len(p) >= 3:
                pts[idx] = np.array([float(p[0]), float(p[1]), float(p[2])], dtype=np.float32)
            else:
                pts[idx] = np.zeros(3, dtype=np.float32)
        else:
            pts[idx] = np.zeros(3, dtype=np.float32)

    # Origin: shoulder midpoint
    l_sh = pts[11]
    r_sh = pts[12]
    midpoint = (l_sh + r_sh) / 2.0
    shoulder_width = np.linalg.norm(l_sh - r_sh)
    if shoulder_width < 1e-4:
        shoulder_width = 1.0

    vec = np.zeros(POSE_DIM, dtype=np.float32)
    # Slot 0: Nose
    vec[0:3] = (pts[0] - midpoint) / shoulder_width
    # Slot 1: Left Shoulder
    vec[3:6] = (pts[11] - midpoint) / shoulder_width
    # Slot 2: Right Shoulder
    vec[6:9] = (pts[12] - midpoint) / shoulder_width
    # Slot 3: Left Elbow
    vec[9:12] = (pts[13] - midpoint) / shoulder_width
    # Slot 4: Right Elbow
    vec[12:15] = (pts[14] - midpoint) / shoulder_width
    # Slot 5: Shoulder Midpoint offset / neck reference
    vec[15:18] = midpoint - pts[0] # Head-to-torso displacement vector

    return vec


def extract_frame_feature_vector(frame_dict, target_dim=TOTAL_FEATURE_DIM):
    """
    Extracts a feature vector from a structured frame dictionary:
    {
        "left_hand": [... 21 landmarks ...],   # Slot 0..62
        "right_hand": [... 21 landmarks ...],  # Slot 63..125
        "pose": [... pose landmarks ...]       # Slot 126..143 (if target_dim >= 144)
    }
    Strict slot assignment: Missing hand produces exact 63 zeros in its slot.
    Never shifts right hand into left hand position.
    """
    vector = np.zeros(target_dim, dtype=np.float32)

    if not isinstance(frame_dict, dict):
        return vector

    # Check for legacy flat 'landmarks' format and parse handedness if present
    if 'landmarks' in frame_dict and 'left_hand' not in frame_dict and 'right_hand' not in frame_dict:
        raw_lms = frame_dict.get('landmarks', [])
        handedness = frame_dict.get('handedness', 'Right')
        if handedness == 'Left':
            vector[0:63] = normalize_hand_landmarks(raw_lms[:21])
        else:
            vector[63:126] = normalize_hand_landmarks(raw_lms[:21])
        if len(raw_lms) >= 42:
            vector[0:63] = normalize_hand_landmarks(raw_lms[21:42])
        return vector

    # Strict slot placement
    if 'left_hand' in frame_dict and frame_dict['left_hand']:
        vector[0:63] = normalize_hand_landmarks(frame_dict['left_hand'])

    if 'right_hand' in frame_dict and frame_dict['right_hand']:
        vector[63:126] = normalize_hand_landmarks(frame_dict['right_hand'])

    if target_dim >= 144 and 'pose' in frame_dict and frame_dict['pose']:
        vector[126:144] = normalize_pose_landmarks(frame_dict['pose'])

    return vector


def build_temporal_sequence(frames_list, seq_len=SEQUENCE_LENGTH, feature_dim=TOTAL_FEATURE_DIM):
    """
    Builds sliding temporal sequence windows of shape (N_windows, seq_len, feature_dim).
    Validates input dimension and handles sequence padding/subsampling.
    """
    if not frames_list:
        return np.zeros((0, seq_len, feature_dim), dtype=np.float32)

    feature_vectors = [extract_frame_feature_vector(f, target_dim=feature_dim) for f in frames_list]
    total_frames = len(feature_vectors)

    if total_frames < seq_len:
        # Pad with last valid frame or zero padding
        padded = np.zeros((seq_len, feature_dim), dtype=np.float32)
        padded[:total_frames] = np.array(feature_vectors, dtype=np.float32)
        if total_frames > 0:
            for k in range(total_frames, seq_len):
                padded[k] = padded[total_frames - 1]
        return np.expand_dims(padded, axis=0)

    # 50% overlap sliding windows
    step = max(1, seq_len // 2)
    windows = []
    for start in range(0, total_frames - seq_len + 1, step):
        window = feature_vectors[start:start + seq_len]
        windows.append(np.array(window, dtype=np.float32))

    if not windows:
        windows.append(np.array(feature_vectors[:seq_len], dtype=np.float32))

    return np.array(windows, dtype=np.float32)



def validate_model_input_shape(tensor, expected_dim=TOTAL_FEATURE_DIM, expected_len=SEQUENCE_LENGTH):
    """
    Phase 7: Checks whether tensor matches expected (batch, seq_len, feature_dim).
    Returns (True, None) or (False, error_status).
    """
    if not isinstance(tensor, (np.ndarray, torch.Tensor)):
        return False, "INVALID_INPUT_TYPE"

    shape = tensor.shape
    if len(shape) != 3:
        return False, f"MODEL_INPUT_DIMENSION_ERROR (expected 3D [B, T, D], got {shape})"

    batch, t_len, f_dim = shape[0], shape[1], shape[2]
    if f_dim != expected_dim:
        return False, f"MODEL_INPUT_SHAPE_MISMATCH (expected feature_dim={expected_dim}, got={f_dim})"

    return True, None
