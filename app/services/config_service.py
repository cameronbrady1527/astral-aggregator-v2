from pathlib import Path
import yaml
import os
from typing import Dict, Optional
from dotenv import load_dotenv
from app.models.config_models import SiteConfig, SiteUpdate, SitesConfig
from app.models.url_models import OnboardingResult

class ConfigService:
    """Service for loading and managing application configuration"""
    
    def __init__(self):
        self._sites_config: Optional[SitesConfig] = None
        self._env_loaded = False
        self._load_environment()
    
    def _load_environment(self):
        """Load environment variables from .env file"""
        if not self._env_loaded:
            env_path = Path(__file__).parent.parent.parent / ".env"

            if env_path.exists():
                load_dotenv(env_path)
            else:
                load_dotenv()

            self._env_loaded = True

    def env_var(self, key: str, default: Optional[str] = None, required: bool = False) -> str:
        """Get environment variable with validation"""
        value = os.getenv(key, default)

        if required and not value:
            raise ValueError(f"Required environment variable '{key}' is not set")

        return value

    @property
    def firecrawl_api_key(self) -> str:
        """Get Firecrawl API key from environment"""
        return self.env_var("FIRECRAWL_API_KEY", required=True)

    @property
    def get_openai_api_key(self) -> str:
        """Get OpenAI API key from environment"""
        return self.env_var("OPENAI_API_KEY", required=True)

    @property
    def log_level(self) -> str:
        """Log level from environment"""
        return self.env_var("LOG_LEVEL", default="INFO")

    @property
    def environment(self) -> str:
        """Current environment (development, production, etc.)"""
        return self.env_var("ENVIRONMENT", default="development")

    @property
    def firecrawl_rate_limit_delay(self) -> int:
        """Delay between Firecrawl requests to respect rate limits (in seconds)"""
        return int(self.env_var("FIRECRAWL_RATE_LIMIT_DELAY", default="6"))

    @property
    def firecrawl_adaptive_rate_limit(self) -> bool:
        """Whether to use adaptive rate limiting (recommended: True)"""
        return self.env_var("FIRECRAWL_ADAPTIVE_RATE_LIMIT", default="True").lower() == "true"

    @property
    def firecrawl_min_delay(self) -> float:
        """Minimum delay between requests in seconds (for adaptive rate limiting)"""
        return float(self.env_var("FIRECRAWL_MIN_DELAY", default="0.5"))  # Reduced from 1.0

    @property
    def firecrawl_max_delay(self) -> float:
        """Maximum delay between requests in seconds (for adaptive rate limiting)"""
        return float(self.env_var("FIRECRAWL_MAX_DELAY", default="5.0"))  # Reduced from 10.0

    @property
    def firecrawl_batch_size(self) -> int:
        """Number of URLs to process in each batch (for adaptive rate limiting)"""
        return int(self.env_var("FIRECRAWL_BATCH_SIZE", default="10"))  # Increased from 3

    @property
    def firecrawl_rate_limit_window(self) -> int:
        """Time window in seconds to track rate limit responses (for adaptive rate limiting)"""
        return int(self.env_var("FIRECRAWL_RATE_LIMIT_WINDOW", default="60"))

    @property
    def firecrawl_max_retries(self) -> int:
        """Maximum number of retry attempts for failed URLs (default: 5 for maximum persistence)"""
        return int(self.env_var("FIRECRAWL_MAX_RETRIES", default="5"))

    def load_sites_config(self) -> SitesConfig:
        """Loads the sites configuration from sites.yaml"""
        if self._sites_config is not None:
            return self._sites_config
            
        config_path = Path(__file__).parent.parent.parent / "config" / "sites.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")

        with open(config_path, "r", encoding="utf-8") as file:
            try:
                raw_config = yaml.safe_load(file)
                
                if not isinstance(raw_config, dict):
                    raise ValueError("Invalid configuration format")

                self._sites_config = SitesConfig(**raw_config)

                return self._sites_config

            except yaml.YAMLError as e:
                raise ValueError(f"Error parsing configuration: {e}")
    
    @property
    def all_sites(self) -> Dict[str, SitesConfig]:
        """Get all sites from configuration"""
        config = self.load_sites_config()

        return config.sites
    
    def site(self, site_id: str) -> Optional[SiteConfig]:
        """Get a specific site by ID"""
        return self.all_sites.get(site_id)

    def update_site_config(self, site_id: str, updates: SiteUpdate) -> None:
        """update site configuration and save to sites.yaml"""
        config = self.load_sites_config()

        if site_id not in config.sites:
            # create a new site if it doesn't exist
            config.sites[site_id] = SiteConfig(
                name=updates.name or f"Site {site_id}",
                url=updates.url or "https://waverley.gov.uk",
                sitemap_url=updates.sitemap_url or "https://waverley.gov.uk/sitemap.xml",
                is_sitemap=updates.is_sitemap if updates.is_sitemap is not None else True,  # Default to True for backward compatibility
                is_sitemap_index=updates.is_sitemap_index if updates.is_sitemap_index is not None else False
            )

        # update the site configuration
        current_site = config.sites[site_id]

        # update only the fields that are provided
        update_data = updates.model_dump(exclude_unset=True)

        
        for field, value in update_data.items():
            if hasattr(current_site, field):
                setattr(current_site, field, value)

        # save back to file
        config_path = Path(__file__).parent.parent.parent / "config" / "sites.yaml"
        
        # Convert to basic Python types for safe YAML serialization
        safe_config = config.model_dump(mode='json')

        
        with open(config_path, "w", encoding="utf-8") as file:
            yaml.dump(safe_config, file, default_flow_style=False, indent=2)

        # clear cache to force reload
        self._sites_config = None

    def mark_site_onboarded(self, site_id: str, onboarding_result: OnboardingResult) -> None:
        """Mark a site as onboarded with the onboarding results"""

        
        update = SiteUpdate(
            onboarded=True,
            top_urls=onboarding_result.top_urls,
            onboarding_datetime=onboarding_result.onboarding_time,
            status="onboarded"
        )
        

        self.update_site_config(site_id, update)

    def is_site_onboarded(self, site_id: str) -> bool:
        """Check if a site has been onboarded"""
        site = self.site(site_id)

        return site.onboarded if site else False


# Global instance
config_service = ConfigService()
