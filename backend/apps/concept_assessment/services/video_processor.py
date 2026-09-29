"""
Concept Assessment Video Processor
==================================
Processes student video explanations by reusing the authoritative shared SignRecognitionService.
No duplicated MediaPipe or PyTorch loading logic exists here.
"""

from shared.sign_language.sign_recognition_service import SignRecognitionService


def process_student_explanation_video(video_path: str, min_confidence: float = 0.40) -> dict:
    """
    Decodes video, tracks MediaPipe hand landmarks, runs PyTorch sequence inference,
    and returns recognized sign tokens and reconstructed English transcript.
    Reuses shared SignRecognitionService.
    """
    return SignRecognitionService.process_video_file(video_path, min_confidence=min_confidence)
