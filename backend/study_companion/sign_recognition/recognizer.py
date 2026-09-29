"""
Unified ISL Recognition Dispatcher and Public Engine Interface.

Implements the verified Priority Order:
1. Priority A: IndianSign package (audited for pretrained weights)
2. Priority B: Other pretrained packages (e.g. sign-language-translator - strictly rejecting PSL != ISL)
3. Priority C: Repository verified trained model (sign_classifier.joblib - 29 ISL classes)
4. Priority D: Custom temporal sequence model (BiGRU + Attention)

Exposes the single internal interface:
`recognize_video(video_path, frames_data=None, fps=30.0)`
"""
import logging
from .indian_sign_adapter import IndianSignAdapter
from .slt_adapter import SignLanguageTranslatorAdapter
from .repository_adapter import RepositoryISLAdapter

logger = logging.getLogger(__name__)

# Singletons
_INDIAN_SIGN_ADAPTER = None
_SLT_ADAPTER = None
_REPO_ADAPTER = None

def get_engine_suite():
    global _INDIAN_SIGN_ADAPTER, _SLT_ADAPTER, _REPO_ADAPTER
    if _INDIAN_SIGN_ADAPTER is None:
        _INDIAN_SIGN_ADAPTER = IndianSignAdapter()
    if _SLT_ADAPTER is None:
        _SLT_ADAPTER = SignLanguageTranslatorAdapter()
    if _REPO_ADAPTER is None:
        _REPO_ADAPTER = RepositoryISLAdapter()
    return _INDIAN_SIGN_ADAPTER, _SLT_ADAPTER, _REPO_ADAPTER


def get_active_engine():
    """
    Selects the best available engine strictly adhering to Priority Order:
    A. Genuinely pretrained IndianSign package (if weights and code exist)
    B. Another verified pretrained ISL model (excluding PSL)
    C. Existing repository trained model (sign_classifier.joblib)
    D. Custom model training required
    """
    ind_ad, slt_ad, repo_ad = get_engine_suite()

    # Priority A: IndianSign package
    if ind_ad.is_installed and ind_ad.has_pretrained_weights and ind_ad.status == "MODEL_READY":
        return ind_ad

    # Priority B: SLT package (only if it supports genuine ISL, not PSL)
    if slt_ad.is_installed and slt_ad.supports_isl and slt_ad.status == "MODEL_READY":
        return slt_ad

    # Priority C: Repository verified trained model
    if repo_ad.is_loaded:
        return repo_ad

    # Priority D / Unready
    return repo_ad


def recognize_video(video_path: str = None, frames_data: list = None, fps: float = 30.0) -> dict:
    """
    Internal standard interface for ISL recognition.
    Strictly isolated: does NOT receive reference concept, topic, or expected answer.
    """
    ind_ad, slt_ad, repo_ad = get_engine_suite()
    active_engine = get_active_engine()

    engine_diagnostics = {
        "priority_a_indiansign": ind_ad.get_diagnostics(),
        "priority_b_slt": slt_ad.get_diagnostics(),
        "priority_c_repository": repo_ad.get_diagnostics(),
        "active_engine_name": active_engine.ENGINE_NAME
    }

    if frames_data is not None and hasattr(active_engine, 'recognize_frames'):
        res = active_engine.recognize_frames(frames_data, fps=fps)
    elif video_path and hasattr(active_engine, 'recognize_video'):
        res = active_engine.recognize_video(video_path)
    else:
        res = {
            "success": False,
            "engine": active_engine.ENGINE_NAME,
            "status": "PRETRAINED_MODEL_NOT_AVAILABLE",
            "message": "No suitable pretrained continuous ISL model found.",
            "tokens": [],
            "recognized_signs": [],
            "unknown_segments": 0,
            "segments_analyzed": 0,
            "confidence": None,
            "supported_vocabulary": []
        }

    res["diagnostics"] = engine_diagnostics
    res["vocabulary_size"] = len(res.get("supported_vocabulary", []))
    return res
