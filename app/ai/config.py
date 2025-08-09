# ==============================================================================
# config.py — AI prompt configuration
# ==============================================================================
# Purpose: Configure AI prompts and models for URL analysis
# Sections: Imports, Public API, Main Classes
# ==============================================================================

# ==============================================================================
# Imports
# ==============================================================================

# Astral AI ----
from app.models.url_models import UrlAnalysisRequest, UrlJudgeRequest

# ==============================================================================
# Public exports
# ==============================================================================
__all__ = ["AIConfig"]

# ==============================================================================
# Main Classes
# ==============================================================================

class AIConfig:
    """Configuration for AI prompts and models."""
    
    # Model configurations
    MODELS = {
        "url_analysis": "gpt-4o-mini",
        "url_judge": "gpt-4o-mini"
    }
    
    @classmethod
    def build_analysis_prompt(cls, request: UrlAnalysisRequest) -> str:
        """Build the analysis prompt for URL evaluation."""
        return f"""
        Analyze the following URLs from {request.site_name} and identify the 5 URLs that are most likely to change frequently with new article-worthy content.
        
        Consider factors like:
        - News sections or blog areas
        - Content that gets updated regularly
        - Areas where new articles are published
        - Avoid static pages like "About Us", "Contact", etc.
        
        URLs to analyze: {request.urls}
        
        Return a JSON object with this exact structure:
        {{
            "urls": ["url1", "url2", "url3", "url4", "url5"],
            "reasoning": "Explanation of why these URLs were selected"
        }}
        
        Return exactly 5 URLs that are most likely to change with new content.
        """
    
    @classmethod
    def build_judge_prompt(cls, request: UrlJudgeRequest) -> str:
        """Build the judge prompt for final URL selection."""
        suggestions_text = "\n".join([
            f"Analysis {i+1}: {urls}" 
            for i, urls in enumerate(request.url_suggestions)
        ])
        
        return f"""
        Review the following URL suggestions from multiple AI analyses for {request.site_name}.
        Select the {request.selection_count} URLs that are MOST likely to change frequently with new article-worthy content.
        
        Suggestions:
        {suggestions_text}
        
        Return a JSON object with this exact structure:
        {{
            "urls": ["url1", "url2", "url3", "url4", "url5"],
            "rejected_urls": ["rejected1", "rejected2"],
            "reasoning": "Explanation of why these URLs were selected as the best"
        }}
        
        Return exactly {request.selection_count} URLs that are the best candidates for monitoring.
        """
