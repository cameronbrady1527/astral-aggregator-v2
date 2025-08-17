# ==============================================================================
# openai_client.py — OpenAI API client
# ==============================================================================
# Purpose: Handle OpenAI API communication and authentication
# Sections: Imports, Public API, Main Classes
# ==============================================================================

# ==============================================================================
# Imports
# ==============================================================================

# Standard Library -----
import json
from datetime import datetime
from typing import List

# Third Party -----
from openai import AsyncOpenAI

# Astral AI ----
from app.services.config_service import config_service
from app.models.url_models import (
    UrlAnalysisRequest, 
    UrlAnalysisResponse, 
    UrlJudgeRequest, 
    UrlJudgeResponse,
    OutputURLsWithInfo,
    UrlInfo
)

# ==============================================================================
# Public exports
# ==============================================================================
__all__ = ["OpenAIClient"]

# ==============================================================================
# Main Classes
# ==============================================================================

class OpenAIClient:
    """Thin client for OpenAI API communication."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config_service.get_openai_api_key)
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
    
    async def analyze_urls(self, request: UrlAnalysisRequest, prompt: str, model: str = "gpt-5") -> OutputURLsWithInfo:
        """Raw API call to OpenAI for URL analysis with enhanced error handling."""
        try:
            # Estimate token count to prevent rate limit issues
            estimated_tokens = self._estimate_token_count(prompt)
            if estimated_tokens > 400000:  # Conservative limit
                raise Exception(f"Estimated tokens ({estimated_tokens}) exceed safe limit (400000)")
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing website URLs to identify which pages serve as content discovery hubs - pages that contain links to multiple articles and get updated when new content is published. You should NOT select individual article pages."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=1
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # create UrlInfo objects for the selected URLs (no detection method for AI analysis)
            url_infos = [
                UrlInfo(
                    url=url,
                    detection_methods=[],  # AI analysis doesn't get a detection method
                    detected_at=datetime.now()
                )
                for url in data.get("urls", [])
            ]
            
            return OutputURLsWithInfo(
                urls=url_infos,
                total_count=len(url_infos),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            # Check if it's a rate limit error
            error_str = str(e).lower()
            if "429" in str(e) or "rate limit" in error_str or "too large" in error_str:
                raise Exception(f"OpenAI rate limit exceeded: {str(e)}. Consider reducing batch size.")
            else:
                raise Exception(f"OpenAI analysis API call failed: {str(e)}")
    
    def _estimate_token_count(self, text: str) -> int:
        """Rough estimation of token count (4 characters ≈ 1 token for English text)."""
        # This is a rough approximation - OpenAI's actual tokenization may differ
        # But it's good enough for preventing obvious rate limit issues
        return len(text) // 4
    
    async def judge_selection(self, request: UrlJudgeRequest, prompt: str, model: str = "gpt-5") -> UrlJudgeResponse:
        """Raw API call to OpenAI for URL selection judging with enhanced error handling."""
        try:
            # Estimate token count to prevent rate limit issues
            estimated_tokens = self._estimate_token_count(prompt)
            if estimated_tokens > 400000:  # Conservative limit
                raise Exception(f"Estimated tokens ({estimated_tokens}) exceed safe limit (400000)")
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert judge that reviews multiple AI suggestions and selects the best URLs for monitoring. You should prioritize content discovery hubs - pages that serve as entry points to discover new articles and content, NOT individual article pages."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=1
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            return UrlJudgeResponse(
                selected_urls=data.get("urls", []),
                rejected_urls=data.get("rejected_urls", [])
            )
            
        except Exception as e:
            # Check if it's a rate limit error
            error_str = str(e).lower()
            if "429" in str(e) or "rate limit" in error_str or "too large" in error_str:
                raise Exception(f"OpenAI rate limit exceeded: {str(e)}. Consider reducing batch size.")
            else:
                raise Exception(f"OpenAI judge API call failed: {str(e)}")
