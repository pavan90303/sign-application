"""
Adapter for the 'sign-language-translator' package.
Audits supported sign languages and strictly prevents substituting
Pakistan Sign Language (PSL) for Indian Sign Language (ISL).
"""
import logging

logger = logging.getLogger(__name__)

class SignLanguageTranslatorAdapter:
    """
    Adapter inspecting sign-language-translator package capabilities.
    Enforces the rule that PSL != ISL.
    """
    ENGINE_NAME = "sign-language-translator"

    def __init__(self):
        self.is_installed = False
        self.version = None
        self.supported_languages = []
        self.supports_isl = False
        self.status = "UNCHECKED"
        self._inspect_package()

    def _inspect_package(self):
        try:
            import sign_language_translator as slt
            from importlib.metadata import version
            self.is_installed = True
            self.version = version("sign_language_translator")
            self.supported_languages = [str(lang.value) for lang in list(slt.SignLanguageCodes)]
            
            # Check for Indian Sign Language explicitly
            isl_identifiers = ['isl', 'indian-sign-language', 'indian_sign_language', 'ind']
            for lang_str in self.supported_languages:
                if any(ident in lang_str.lower() for ident in isl_identifiers):
                    self.supports_isl = True
                    break

            if not self.supports_isl:
                logger.warning(
                    f"[SLTAdapter] sign-language-translator only supports: {self.supported_languages}. "
                    "Pakistan Sign Language (PSL) cannot be used as Indian Sign Language (ISL). Rejecting."
                )
                self.status = "PSL_NOT_ISL_REJECTED"
            else:
                self.status = "MODEL_READY"
        except ImportError:
            self.is_installed = False
            self.status = "NOT_INSTALLED"
        except Exception as e:
            self.is_installed = False
            self.status = f"ERROR: {e}"

    def get_diagnostics(self) -> dict:
        return {
            "engine": self.ENGINE_NAME,
            "installed": self.is_installed,
            "version": self.version,
            "supported_languages": self.supported_languages,
            "supports_isl": self.supports_isl,
            "status": self.status
        }

    def recognize_video(self, video_path: str) -> dict:
        return {
            "success": False,
            "engine": self.ENGINE_NAME,
            "status": "PSL_NOT_ISL_REJECTED",
            "message": "sign-language-translator only supports Pakistan Sign Language (PSL != ISL).",
            "tokens": [],
            "unknown_segments": 0,
            "segments_analyzed": 0,
            "confidence": None,
            "supported_vocabulary": []
        }
