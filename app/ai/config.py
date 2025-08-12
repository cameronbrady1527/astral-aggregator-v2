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
        "url_analysis": "gpt-5",
        "url_judge": "gpt-5"
    }
    
    @classmethod
    def build_analysis_prompt(cls, request: UrlAnalysisRequest) -> str:
        """Build the analysis prompt for URL evaluation."""
        return f"""
        Analyze the following URLs from {request.site_name} and identify the 5 URLs that are most likely to serve as content discovery hubs for new articles and pages.
        
        You want URLs that are:
        - Content section pages (like /news/, /blog/, /press-releases/, /judgments/, /articles/)
        - Archive or index pages where new content gets added
        - Dynamic content aggregators (pages with terms like "latest", "recent", "updates", "announcements")
        - Pages that serve as entry points to discover new content, even if they're subsections
        - NOT individual article pages or static content pages
        - NOT pages like "About Us", "Contact", "Privacy Policy", "Terms of Service"
        
        Good examples:
        - /news/ (news section homepage)
        - /blog/ (blog index page)
        - /press-releases/ (press release archive)
        - /judgments/ (judgment archive)
        - /publications/ (publications index)
        - /reports/ (reports archive)
        - /latest-news/ (recent news aggregator)
        - /announcements/ (announcement hub)
        - /whats-new/ (new content showcase)
        
        Bad examples:
        - /news/specific-article-title (individual article)
        - /blog/2024/01/specific-post (individual blog post)
        - /about-us (static page)
        - /contact (static page)
        - /privacy-policy (static page)
        
        Look for:
        - Pages that aggregate multiple pieces of content
        - URLs with dynamic content indicators (latest, recent, updates, news)
        - Both main sections AND valuable subsections that serve as content discovery points
        - Pages that would be bookmarked by users wanting to check for new content
        
        URLs to analyze: {request.urls}
        
        Return a JSON object with this exact structure:
        {{
            "urls": ["url1", "url2", "url3", "url4", "url5"],
            "reasoning": "Explanation of why these URLs were selected as content discovery hubs"
        }}
        
        Return exactly 5 URLs that are content discovery hubs, not individual articles.
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
        Select the {request.selection_count} URLs that are BEST content discovery hubs for finding new articles and pages.
        
        A good content discovery hub:
        - Is a section/archive page (like /news/, /blog/, /press-releases/)
        - Contains links to multiple articles or content pieces
        - Gets updated when new content is published
        - Serves as an entry point to discover new content
        - May be a subsection that aggregates content
        - Has dynamic content indicators in the URL or purpose
        - Is NOT an individual article page
        - Would be useful for users wanting to check for new content regularly
        
        When evaluating URLs, prioritize:
        1. **Content density**: Pages that link to many articles
        2. **Update frequency**: Pages that are likely updated regularly
        3. **User discoverability**: How easily users can find new content
        4. **Content aggregation**: Pages that serve as content showcases
        5. **Hierarchical value**: Both main sections and valuable subsections
        
        Suggestions:
        {suggestions_text}
        
        Return a JSON object with this exact structure:
        {{
            "urls": ["url1", "url2", "url3", "url4", "url5"],
            "rejected_urls": ["rejected1", "rejected2"],
            "reasoning": "Explanation of why these URLs are the best content discovery hubs"
        }}
        
        Return exactly {request.selection_count} URLs that are content discovery hubs, not individual articles.
        """
