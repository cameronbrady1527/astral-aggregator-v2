from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from app.services.config_service import config_service

router = APIRouter(prefix="/api/v1", tags=["urls"])

@router.get("/sites")
def list_sites():
    """List all available sites from yaml.config"""
    sites = config_service.get_sites()
    
    return {
        site_id: {
            "name": site_info.get("name", "Unknown"),
            "url": site_info.get("url", "Unknown"),
            "sitemap_url": site_info.get("sitemap_url", "Unknown"),
            "is_sitemap_index": site_info.get("is_sitemap_index", False)
        }
        for site_id, site_info in sites.items()
    }

@router.post("/trigger/{site_id}")
async def extract_urls(site_id: str):
    """Extracts URLs from a given site (or all)"""    
    # validate site_id is a valid site from the list of our sites
    if site_id != "all" and site_id not in config_service.get_sites():
        return { 
            "error": f"Site {site_id} not found in configuration. If you would like to add it, please add to sites.yaml. See other site configuration or sites_example.yaml for reference." 
        }

    site_info = config_service.get_site(site_id) if site_id != "all" else None
    

    # check if the site has been run by the system before (if not, onboard: AI to determine most-likely to change)
    # TODO: Implement onboarding logic

    # TODO: Implement URL extraction logic
    
    # temporary success return
    return {
        "site_id": site_id,
        "site_url": site_info["url"] if site_info else "all sites",
        "status": "triggered"    
    }
