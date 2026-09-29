"""
Alphabet Recognizer Module
==========================
Wrapper for single-frame ISL fingerspelling recognition (A-Z).
"""

from shared.sign_language.sign_recognition_service import SignRecognitionService


class AlphabetRecognizer:
    @classmethod
    def predict(cls, landmarks, handedness='Right', threshold=0.40):
        return SignRecognitionService.predict_alphabet(landmarks, handedness=handedness)
