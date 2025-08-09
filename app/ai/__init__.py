# ==============================================================================
# ai/__init__.py — AI Components
# ==============================================================================
# Purpose: AI-powered URL analysis and judging components
# ==============================================================================

from .config import AIConfig
from .url_judge import UrlJudge

__all__ = [
    'AIConfig',
    'UrlJudge',
]
