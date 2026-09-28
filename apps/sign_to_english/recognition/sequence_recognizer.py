"""
Sequence Recognizer Module
==========================
Wrapper for temporal sequence model inference over landmark windows and video files.
"""

from shared.sign_language.sign_recognition_service import SignRecognitionService


class SequenceRecognizer:
    @classmethod
    def predict_window(cls, frames_buffer, threshold=0.55):
        return SignRecognitionService.predict_sequence(frames_buffer, threshold=threshold)

    @classmethod
    def process_video(cls, video_path, min_confidence=0.40):
        return SignRecognitionService.process_video_file(video_path, min_confidence=min_confidence)
