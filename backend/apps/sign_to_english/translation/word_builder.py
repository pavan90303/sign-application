"""
Word Builder Service
====================
Buffers fingerspelled ISL letters and assists with non-destructive dictionary suggestions.
"""

from shared.sign_language.sign_recognition_service import SignRecognitionService


class WordBuilder:
    """Manages letter stream and suggestions for fingerspelling mode."""

    def __init__(self):
        self.buffer = []

    def add_letter(self, letter: str):
        if letter and len(letter) == 1 and letter.isalpha():
            self.buffer.append(letter.upper())

    def get_current_word(self) -> str:
        return "".join(self.buffer)

    def backspace(self):
        if self.buffer:
            self.buffer.pop()

    def clear(self):
        self.buffer = []

    def get_suggestions(self, top_n: int = 5) -> list:
        return SignRecognitionService.suggest_words(self.get_current_word(), top_n=top_n)
