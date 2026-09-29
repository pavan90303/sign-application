"""
Training Script for ISL Alphabet Classifier (A-Z)
=================================================
Extracts real MediaPipe hand landmarks from course video assets (assets/A.mp4 - assets/Z.mp4),
applies canonical preprocessing (handedness canonicalization, palm scale normalization, 86-dim features),
augments samples with 3D rotations, scaling, and jitter, and trains both:
1. PyTorch Deep Neural Network (MLP with BatchNorm, LeakyReLU, Dropout)
2. Calibrated Random Forest Classifier
Saves model weights, label mappings, and evaluation metrics (precision, recall, f1, accuracy).
"""

import os
import sys
import json
import pickle
import string
import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import joblib

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from study_companion.isl_preprocessing import (
    extract_isl_features,
    augment_landmarks,
    canonicalize_handedness,
    parse_raw_landmarks,
    FEATURE_DIM,
)

# Output paths
MODELS_DIR = os.path.join(BASE_DIR, 'study_companion', 'ml_models')
os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_TASK_PATH = os.path.join(MODELS_DIR, 'hand_landmarker.task')
PYTORCH_MODEL_PATH = os.path.join(MODELS_DIR, 'isl_alphabet_model.pt')
RF_MODEL_PATH = os.path.join(MODELS_DIR, 'isl_alphabet_rf.joblib')
LABELS_PATH = os.path.join(MODELS_DIR, 'alphabet_labels.json')
CONFIG_PATH = os.path.join(MODELS_DIR, 'alphabet_model_config.json')
EVALUATION_PATH = os.path.join(MODELS_DIR, 'alphabet_evaluation.json')
CACHE_PATH = os.path.join(MODELS_DIR, 'raw_alphabet_landmarks.pkl')


class ISLAlphabetMLP(nn.Module):
    """
    Deep PyTorch Classifier for 86-dim ISL Handshape Features -> 26 classes (A-Z).
    """
    def __init__(self, input_dim=86, num_classes=26):
        super(ISLAlphabetMLP, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(0.1),
            nn.Dropout(0.20),
            
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.LeakyReLU(0.1),
            nn.Dropout(0.15),
            
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.LeakyReLU(0.1),
            nn.Dropout(0.10),
            
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        return self.net(x)


def extract_landmarks_from_videos():
    """
    Extracts raw 21 3D landmarks for all 26 letters from assets/{letter}.mp4,
    or loads from cache if already extracted.
    """
    if os.path.exists(CACHE_PATH):
        print(f"Loading cached video landmarks from {CACHE_PATH}...")
        with open(CACHE_PATH, 'rb') as f:
            return pickle.load(f)

    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    base_options = python.BaseOptions(model_asset_path=MODEL_TASK_PATH)
    options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=2)
    detector = vision.HandLandmarker.create_from_options(options)

    raw_data = {}  # letter -> list of (raw_landmarks_21x3, handedness)
    print("=" * 60)
    print("EXTRACTING REAL LANDMARKS FROM ALPHABET VIDEOS (A-Z)...")
    print("=" * 60)

    for ch in string.ascii_uppercase:
        video_path = os.path.join(BASE_DIR, 'assets', f'{ch}.mp4')
        if not os.path.exists(video_path):
            video_path = os.path.join(BASE_DIR, 'assets', 'signs', f'{ch}.mp4')
            if not os.path.exists(video_path):
                print(f"[!] Warning: Video for letter {ch} not found!")
                continue

        cap = cv2.VideoCapture(video_path)
        samples = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = detector.detect(mp_img)

            if result.hand_landmarks and len(result.hand_landmarks) > 0:
                landmarks_proto = result.hand_landmarks[0]
                handedness = 'Right'
                if result.handedness and len(result.handedness) > 0:
                    handedness = result.handedness[0][0].category_name

                pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks_proto], dtype=np.float32)
                samples.append((pts, handedness))

        cap.release()
        raw_data[ch] = samples
        print(f"Letter '{ch}': Extracted {len(samples)} valid hand frames from {frame_idx} video frames.")

    # Cache for future runs
    with open(CACHE_PATH, 'wb') as f:
        pickle.dump(raw_data, f)
    print(f"Saved raw landmarks cache to {CACHE_PATH}")

    return raw_data


def build_augmented_dataset(raw_data, augmentations_per_frame=16):
    """
    Builds the feature matrix X and label vector y using ISL canonical features and data augmentation.
    """
    labels = list(string.ascii_uppercase)
    label_to_idx = {ch: i for i, ch in enumerate(labels)}

    X_list = []
    y_list = []

    print("\nApplying preprocessing, handedness normalization, and geometric data augmentation...")
    for ch, samples in raw_data.items():
        ch_idx = label_to_idx[ch]
        for pts, handedness in samples:
            # 1. Base canonical feature
            base_feat = extract_isl_features(pts, handedness=handedness)
            X_list.append(base_feat)
            y_list.append(ch_idx)

            # 2. Augmented versions
            for _ in range(augmentations_per_frame):
                aug_pts = augment_landmarks(pts, angle_deg_max=12.0, scale_min=0.90, scale_max=1.10, jitter_std=0.012)
                aug_feat = extract_isl_features(aug_pts, handedness=handedness)
                X_list.append(aug_feat)
                y_list.append(ch_idx)

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int64)
    print(f"Total dataset shape: X={X.shape}, y={y.shape} ({len(labels)} classes)")
    return X, y, labels


def train_models():
    # 1. Extract landmarks from real video files (or cache)
    raw_data = extract_landmarks_from_videos()

    # 2. Build augmented feature dataset
    X, y, labels = build_augmented_dataset(raw_data, augmentations_per_frame=16)

    # 3. Train / Val / Test Split (70% / 15% / 15%)
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=0.1765, random_state=42, stratify=y_train_val
    )

    print(f"Train samples: {len(X_train)} | Val samples: {len(X_val)} | Test samples: {len(X_test)}")

    # 4. Train Calibrated Random Forest Classifier
    print("\nTraining Calibrated Random Forest Classifier...")
    rf_clf = RandomForestClassifier(n_estimators=150, max_depth=25, random_state=42, n_jobs=-1)
    rf_clf.fit(X_train, y_train)

    rf_test_preds = rf_clf.predict(X_test)
    rf_test_acc = float(accuracy_score(y_test, rf_test_preds))
    print(f"Random Forest Test Accuracy: {rf_test_acc * 100:.2f}%")

    # 5. Train PyTorch Deep MLP
    print("\nTraining PyTorch Deep Neural Network (ISLAlphabetMLP)...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using compute device: {device}")

    mlp_model = ISLAlphabetMLP(input_dim=FEATURE_DIM, num_classes=len(labels)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(mlp_model.parameters(), lr=2e-3, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=4)

    train_dataset = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
    val_dataset = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))
    test_dataset = TensorDataset(torch.from_numpy(X_test), torch.from_numpy(y_test))

    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=128, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)

    best_val_acc = 0.0
    epochs = 35

    for epoch in range(1, epochs + 1):
        mlp_model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            outputs = mlp_model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * batch_x.size(0)
            _, preds = torch.max(outputs, 1)
            correct += (preds == batch_y).sum().item()
            total += batch_y.size(0)

        train_acc = correct / total

        # Validation
        mlp_model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for vx, vy in val_loader:
                vx, vy = vx.to(device), vy.to(device)
                v_out = mlp_model(vx)
                _, v_preds = torch.max(v_out, 1)
                val_correct += (v_preds == vy).sum().item()
                val_total += vy.size(0)

        val_acc = val_correct / val_total
        scheduler.step(val_acc)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                'model_state_dict': mlp_model.state_dict(),
                'input_dim': FEATURE_DIM,
                'num_classes': len(labels),
                'labels': labels,
                'val_acc': val_acc
            }, PYTORCH_MODEL_PATH)

        if epoch % 5 == 0 or epoch == epochs:
            print(f"Epoch [{epoch:02d}/{epochs}] Loss: {total_loss/total:.4f} | Train Acc: {train_acc*100:.2f}% | Val Acc: {val_acc*100:.2f}% (Best: {best_val_acc*100:.2f}%)")

    # 6. Final Evaluation on Held-Out Test Split
    print("\n" + "=" * 60)
    print("FINAL EVALUATION ON HELD-OUT TEST SPLIT (15%)")
    print("=" * 60)

    # Load best PyTorch model
    checkpoint = torch.load(PYTORCH_MODEL_PATH, map_location=device)
    mlp_model.load_state_dict(checkpoint['model_state_dict'])
    mlp_model.eval()

    all_preds = []
    all_targets = []
    with torch.no_grad():
        for tx, ty in test_loader:
            tx = tx.to(device)
            out = mlp_model(tx)
            _, p = torch.max(out, 1)
            all_preds.extend(p.cpu().numpy())
            all_targets.extend(ty.numpy())

    mlp_test_acc = float(accuracy_score(all_targets, all_preds))
    report_dict = classification_report(all_targets, all_preds, target_names=labels, output_dict=True)
    report_text = classification_report(all_targets, all_preds, target_names=labels)
    cm = confusion_matrix(all_targets, all_preds).tolist()

    print(f"PyTorch Deep MLP Test Accuracy: {mlp_test_acc * 100:.2f}%")
    print(f"Random Forest Test Accuracy:    {rf_test_acc * 100:.2f}%")
    print("\nClassification Report (PyTorch):")
    print(report_text)

    # Save Random Forest Model
    joblib.dump({
        'model': rf_clf,
        'labels': labels,
        'accuracy': rf_test_acc
    }, RF_MODEL_PATH)

    # Save Labels Mapping
    with open(LABELS_PATH, 'w') as f:
        json.dump({
            "labels": labels,
            "classes_count": len(labels),
            "label_to_idx": {ch: i for i, ch in enumerate(labels)}
        }, f, indent=2)

    # Save Model Config
    with open(CONFIG_PATH, 'w') as f:
        json.dump({
            "feature_dim": FEATURE_DIM,
            "num_classes": len(labels),
            "architecture": "ISLAlphabetMLP",
            "pytorch_weights": "isl_alphabet_model.pt",
            "rf_model": "isl_alphabet_rf.joblib",
            "device": str(device),
            "best_val_accuracy": float(best_val_acc),
            "test_accuracy": float(mlp_test_acc),
            "rf_test_accuracy": float(rf_test_acc)
        }, f, indent=2)

    # Save Evaluation Report
    with open(EVALUATION_PATH, 'w') as f:
        json.dump({
            "accuracy": float(mlp_test_acc),
            "rf_accuracy": float(rf_test_acc),
            "classification_report": report_dict,
            "confusion_matrix": cm,
            "sample_counts": {
                "total": int(len(X)),
                "train": int(len(X_train)),
                "val": int(len(X_val)),
                "test": int(len(X_test))
            }
        }, f, indent=2)

    print("\nAll model artifacts saved successfully to study_companion/ml_models/!")
    print(f"- PyTorch Model: {PYTORCH_MODEL_PATH}")
    print(f"- RF Model:      {RF_MODEL_PATH}")
    print(f"- Labels:        {LABELS_PATH}")
    print(f"- Config:        {CONFIG_PATH}")
    print(f"- Evaluation:    {EVALUATION_PATH}")


if __name__ == '__main__':
    train_models()
