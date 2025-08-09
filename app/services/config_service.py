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
        if self._env_loaded:
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
    
    @property
    def site(self, site_id: str) -> Optional[SiteConfig]:
        """Get a specific site by ID"""
        return self.all_sites().get(site_id)

    def update_site_config(self, site_id: str, updates: SiteUpdate) -> None:
        """update site configuration and save to sites.yaml"""
        config = self.load_sites_config()

        if site_id not in config.sites:
            # create a new site if it doesn't exist
            config.sites[site_id] = SitesConfig(
                name=updates.name or f"Site {site_id}",
                url=updates.url or "https://waverley.gov.uk",
                sitemap_url=updates.sitemap_url or "https://waverley.gov.uk/sitemap.xml"
            )

        # update the site configuration
        current_site = config.sites[site_id]

        # update only the fields that are provided
        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(current_site, field, value)

        # save back to file
        config_path = Path(__file__).parent.parent.parent / "config" / "sites.yaml"
        with open(config_path, "w", encoding="utf-8") as file:
            yaml.dump(config.dict(), file, default_flow_style=False, indent=2)

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
