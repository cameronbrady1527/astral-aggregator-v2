from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, field_validator
from urllib.parse import urlparse
from pathlib import Path
import yaml
from typing import Dict, Any


app = FastAPI()

# load configuration
def load_sites_config() -> Dict[str, Any]:
    """Loads the sites configuration from sites.yaml"""
    config_path = Path(__file__).parent.parent / "config" / "sites.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {config_path}")

    with open(config_path, "r", encoding="utf-8") as file:
        try:
            config = yaml.safe_load(file)
            if not isinstance(config, dict):
                raise ValueError("Invalid configuration format")
            return config
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing configuration: {e}")

    return config

sites_config = load_sites_config()

@app.get("/")
def read_root():
    return { "Hello": "Cam" }



    return n * get_factorial(n - 1)

@app.get("/items/{item_id}")
def read_item(item_id: int):
    def get_factorial(n: int):
        if n == 0:
            return 1
        return n * get_factorial(n - 1)
    
    return { "item_id": f"{item_id}! = {get_factorial(item_id)}" }


@app.get("/sites")
def list_sites():
    """List all available sites from yaml.config"""
    sites = sites_config.get("sites", {})
    
    return {
        site_id: {
            "name": site_info.get("name", "Unknown"),
            "url": site_info.get("url", "Unknown"),
            "sitemap_url": site_info.get("sitemap_url", "Unknown"),
            "is_sitemap_index": site_info.get("is_sitemap_index", False)
        }
        for site_id, site_info in sites.items()
    }


@app.post("/trigger/{site_id}")
async def extract_urls(site_id: str):
    """Extracts URLs from a given site (or all)"""
    # validate site_id is a valid site from the list of our sites
    if site_id != "all" and site_id not in sites_config.get("sites", {}):
        return { "error": f"Site {site_id} not found in configuration" }

    # temporary return
    return {
        "site_id": site_id,
        "site_url": sites_config["sites"][site_id]["url"],
        "status": "triggered"    
    }