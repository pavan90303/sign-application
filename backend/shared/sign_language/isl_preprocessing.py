"""
ISL Preprocessing Pipeline & Feature Extractor
==============================================
Unified Source of Truth for Indian Sign Language Fingerspelling (A-Z).
Provides identical feature extraction for both offline training and live inference.

Key features:
1. Handedness canonicalization: Left hands are mirrored (x -> -x) to match canonical Right hand representation.
2. Translation invariance: Wrist landmark (0) is shifted to local origin (0, 0, 0).
3. Scale invariance: Landmarks are scaled by palm dimension (wrist to middle MCP).
4. Rich 86-dimensional geometric features:
   - 63 values: Normalized 3D coordinates (21 * 3) centered at wrist and scaled by palm
   - 5 values: Fingertip-to-wrist euclidean distances (Thumb, Index, Middle, Ring, Pinky)
   - 5 values: Inter-fingertip distances (Thumb-Index, Index-Middle, Middle-Ring, Ring-Pinky, Thumb-Pinky span)
   - 5 values: Finger extension ratios (tip-to-wrist / mcp-to-wrist)
   - 5 values: Finger curl cosines (angle along finger joints for Thumb, Index, Middle, Ring, Pinky)
   - 3 values: Palm plane normal unit vector (cross product of wrist->index and wrist->pinky)
   - Total: 63 + 5 + 5 + 5 + 5 + 3 = 86 features
"""

import os
import math
import numpy as np
import logging

logger = logging.getLogger(__name__)

FEATURE_DIM = 86
NUM_LANDMARKS = 21

FINGERTIP_INDICES = [4, 8, 12, 16, 20]      # Thumb, Index, Middle, Ring, Pinky tips
MCP_INDICES = [2, 5, 9, 13, 17]             # Thumb CMC/MCP, Index MCP, Middle MCP, Ring MCP, Pinky MCP
PIP_INDICES = [3, 6, 10, 14, 18]            # Thumb IP, Index PIP, Middle PIP, Ring PIP, Pinky PIP


def parse_raw_landmarks(landmarks):
    """
    Parses various input landmark formats (list of dicts, numpy array, list of tuples)
    into a standard (21, 3) float32 numpy array.
    """
    if landmarks is None:
        return np.zeros((NUM_LANDMARKS, 3), dtype=np.float32)

    if isinstance(landmarks, np.ndarray):
        arr = landmarks.astype(np.float32)
        if arr.ndim == 1:
            arr = arr.reshape(-1, 3)
        if arr.shape[0] < NUM_LANDMARKS:
            pad = np.zeros((NUM_LANDMARKS - arr.shape[0], 3), dtype=np.float32)
            arr = np.vstack([arr, pad])
        return arr[:NUM_LANDMARKS, :3]

    pts = np.zeros((NUM_LANDMARKS, 3), dtype=np.float32)
    for i in range(min(len(landmarks), NUM_LANDMARKS)):
        p = landmarks[i]
        if isinstance(p, dict):
            pts[i] = [float(p.get('x', 0.0)), float(p.get('y', 0.0)), float(p.get('z', 0.0))]
        elif isinstance(p, (list, tuple)):
            if len(p) >= 3:
                pts[i] = [float(p[0]), float(p[1]), float(p[2])]
            elif len(p) == 2:
                pts[i] = [float(p[0]), float(p[1]), 0.0]
    return pts


def canonicalize_handedness(pts, handedness='Right'):
    """
    Ensures single canonical orientation by mirroring Left hands along the X axis.
    This guarantees that both Left-handed and Right-handed signers produce identical handshape features.
    """
    pts_copy = pts.copy()
    if handedness and str(handedness).strip().lower() == 'left':
        # Mirror X coordinate across vertical axis
        pts_copy[:, 0] = -pts_copy[:, 0]
    return pts_copy


def normalize_hand_geometry(pts):
    """
    Translates wrist to origin and scales by palm distance (wrist -> middle finger MCP).
    Returns (21, 3) normalized float32 array.
    """
    wrist = pts[0].copy()
    centered = pts - wrist

    # Middle MCP index 9 distance from wrist
    palm_scale = np.linalg.norm(centered[9])
    if palm_scale < 1e-4:
        # Fallback to Index MCP index 5
        palm_scale = np.linalg.norm(centered[5])
        if palm_scale < 1e-4:
            palm_scale = 1.0

    return centered / palm_scale


def compute_vector_cos_angle(v1, v2):
    """Computes cosine of angle between two 3D vectors."""
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 < 1e-5 or n2 < 1e-5:
        return 1.0
    cos_val = np.dot(v1, v2) / (n1 * n2)
    return float(np.clip(cos_val, -1.0, 1.0))


def extract_isl_features(landmarks, handedness='Right'):
    """
    Extracts the canonical 86-dimensional feature vector from 21 hand landmarks:
    - 63 values: Normalized 3D coordinates (21 * 3) centered at wrist and scaled by palm
    - 5 values: Fingertip-to-wrist euclidean distances (Thumb, Index, Middle, Ring, Pinky)
    - 5 values: Inter-fingertip distances (Thumb-Index, Index-Middle, Middle-Ring, Ring-Pinky, Thumb-Pinky span)
    - 5 values: Finger extension ratios (tip-to-wrist / mcp-to-wrist)
    - 5 values: Finger curl cosines (joint angles for 5 fingers)
    - 3 values: Palm plane normal unit vector (cross product of wrist->index and wrist->pinky)
    - Total: 63 + 5 + 5 + 5 + 5 + 3 = 86 features
    """
    pts = parse_raw_landmarks(landmarks)
    pts = canonicalize_handedness(pts, handedness=handedness)
    pts_norm = normalize_hand_geometry(pts)

    # 1. Normalized coordinates (63)
    flat_coords = pts_norm.flatten().tolist()

    # 2. Fingertip-to-wrist distances (5)
    tip_to_wrist = [float(np.linalg.norm(pts_norm[t])) for t in FINGERTIP_INDICES]

    # 3. Inter-fingertip distances (5)
    inter_tip_dists = [
        float(np.linalg.norm(pts_norm[4] - pts_norm[8])),    # Thumb to Index
        float(np.linalg.norm(pts_norm[8] - pts_norm[12])),   # Index to Middle
        float(np.linalg.norm(pts_norm[12] - pts_norm[16])),  # Middle to Ring
        float(np.linalg.norm(pts_norm[16] - pts_norm[20])),  # Ring to Pinky
        float(np.linalg.norm(pts_norm[4] - pts_norm[20]))    # Thumb to Pinky span
    ]

    # 4. Finger extension ratios (5)
    extension_ratios = [
        float(np.linalg.norm(pts_norm[t]) / (np.linalg.norm(pts_norm[m]) + 1e-4))
        for t, m in zip(FINGERTIP_INDICES, MCP_INDICES)
    ]

    # 5. Finger curl cosines (5)
    # Cosine between lower segment (MCP->PIP) and upper segment (PIP->TIP)
    curl_cosines = [
        compute_vector_cos_angle(pts_norm[2] - pts_norm[1], pts_norm[4] - pts_norm[3]),   # Thumb
        compute_vector_cos_angle(pts_norm[6] - pts_norm[5], pts_norm[8] - pts_norm[6]),   # Index
        compute_vector_cos_angle(pts_norm[10] - pts_norm[9], pts_norm[12] - pts_norm[10]), # Middle
        compute_vector_cos_angle(pts_norm[14] - pts_norm[13], pts_norm[16] - pts_norm[14]),# Ring
        compute_vector_cos_angle(pts_norm[18] - pts_norm[17], pts_norm[20] - pts_norm[18]) # Pinky
    ]

    # 6. Palm plane normal vector (3)
    v_index = pts_norm[5] - pts_norm[0]
    v_pinky = pts_norm[17] - pts_norm[0]
    normal = np.cross(v_index, v_pinky)
    normal_len = np.linalg.norm(normal)
    palm_normal = (normal / (normal_len + 1e-4)).tolist()

    vec = flat_coords + tip_to_wrist + inter_tip_dists + extension_ratios + curl_cosines + palm_normal
    return np.array(vec, dtype=np.float32)


def augment_landmarks(pts, angle_deg_max=12.0, scale_min=0.90, scale_max=1.10, jitter_std=0.012):
    """
    Applies realistic 3D geometric augmentation to hand landmarks:
    - In-plane and slight out-of-plane rotation (+-angle_deg_max)
    - Scale variation [scale_min, scale_max]
    - Additive Gaussian noise (jitter)
    """
    aug = pts.copy()

    # 1. 2D/3D Rotation
    angle_z = np.radians(np.random.uniform(-angle_deg_max, angle_deg_max))
    angle_y = np.radians(np.random.uniform(-angle_deg_max * 0.35, angle_deg_max * 0.35))
    
    # Rotation matrix around Z
    cos_z, sin_z = np.cos(angle_z), np.sin(angle_z)
    R_z = np.array([
        [cos_z, -sin_z, 0],
        [sin_z, cos_z, 0],
        [0, 0, 1]
    ], dtype=np.float32)

    # Rotation matrix around Y
    cos_y, sin_y = np.cos(angle_y), np.sin(angle_y)
    R_y = np.array([
        [cos_y, 0, sin_y],
        [0, 1, 0],
        [-sin_y, 0, cos_y]
    ], dtype=np.float32)

    R = R_z @ R_y
    aug = aug @ R.T

    # 2. Scaling
    scale = np.random.uniform(scale_min, scale_max)
    aug = aug * scale

    # 3. Additive Gaussian jitter (leaving wrist relatively anchored)
    noise = np.random.normal(0.0, jitter_std, aug.shape).astype(np.float32)
    noise[0] = 0.0  # keep wrist stationary
    aug = aug + noise

    return aug
