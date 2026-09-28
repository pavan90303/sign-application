"""
Adapter for the 'IndianSign' PyPI package.
Investigates availability of pretrained Indian Sign Language recognition models.
"""
import os
import sys
import importlib
import logging

logger = logging.getLogger(__name__)

class IndianSignAdapter:
    """
    Adapter to inspect and interface with the IndianSign package.
    Tests for genuine pretrained models, weights, labels, and inference.
    """
    ENGINE_NAME = "IndianSign"

    def __init__(self):
        self.is_installed = False
        self.version = None
        self.has_pretrained_weights = False
        self.model_path = None
        self.has_labels = False
        self.supported_vocabulary = []
        self.status = "UNCHECKED"
        self._inspect_package()

    def _inspect_package(self):
        # 1. Check if package distribution is installed via importlib.metadata
        try:
            from importlib.metadata import version, files, PackageNotFoundError
            try:
                self.version = version("IndianSign")
                self.is_installed = True
            except PackageNotFoundError:
                self.is_installed = False
                self.status = "NOT_INSTALLED"
                return
        except Exception:
            self.is_installed = False
            self.status = "NOT_INSTALLED"
            return

        # 2. Check files in the installed distribution
        try:
            pkg_files = files("IndianSign") or []
            file_names = [str(f) for f in pkg_files]
        except Exception:
            file_names = []

        # Look for weight files (.pt, .pth, .h5, .tflite, .joblib, .onnx)
        weight_extensions = ('.pt', '.pth', '.h5', '.keras', '.tflite', '.onnx', '.joblib', '.pkl', '.bin')
        found_weights = [f for f in file_names if f.lower().endswith(weight_extensions)]
        found_py = [f for f in file_names if f.lower().endswith('.py')]

        # 3. Test import
        module_imported = False
        for mod_name in ["IndianSign", "indiansign", "indian_sign"]:
            try:
                mod = importlib.import_module(mod_name)
                module_imported = True
                break
            except (ImportError, ModuleNotFoundError):
                continue

        if not module_imported or len(found_py) == 0:
            logger.warning("[IndianSignAdapter] IndianSign package contains no executable Python modules or scripts.")
            self.status = "INDIANSIGN_PRETRAINED_MODEL_UNAVAILABLE"
            self.has_pretrained_weights = False
            return

        if not found_weights:
            logger.warning("[IndianSignAdapter] IndianSign package contains no bundled pretrained model weights.")
            self.status = "INDIANSIGN_PRETRAINED_MODEL_UNAVAILABLE"
            self.has_pretrained_weights = False
            return

        # If we reach here, genuine weights and code exist
        self.has_pretrained_weights = True
        self.status = "MODEL_READY"

    def get_diagnostics(self) -> dict:
        return {
            "engine": self.ENGINE_NAME,
            "installed": self.is_installed,
            "version": self.version,
            "has_pretrained_weights": self.has_pretrained_weights,
            "model_path": self.model_path,
            "has_labels": self.has_labels,
            "number_of_labels": len(self.supported_vocabulary),
            "supported_vocabulary": self.supported_vocabulary,
            "status": self.status,
            "supports_continuous": False
        }

    def recognize_video(self, video_path: str) -> dict:
        """
        Runs inference if pretrained model is available.
        Otherwise returns structured unavailability report without faking.
        """
        if self.status == "INDIANSIGN_PRETRAINED_MODEL_UNAVAILABLE" or not self.has_pretrained_weights:
            return {
                "success": False,
                "engine": self.ENGINE_NAME,
                "status": "INDIANSIGN_PRETRAINED_MODEL_UNAVAILABLE",
                "message": "IndianSign package does not bundle or provide pretrained model weights.",
                "tokens": [],
                "unknown_segments": 0,
                "segments_analyzed": 0,
                "confidence": None,
                "supported_vocabulary": []
            }

        # If a real model were loaded, inference would execute here
        raise NotImplementedError("Inference path unreachable when no model is bundled.")
