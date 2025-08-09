# ==============================================================================
# url_router.py — URL processing endpoints
# ==============================================================================
# Purpose: Handle URL processing API endpoints
# Sections: Imports, Public API, Router definition
# ==============================================================================

# ==============================================================================
# Imports
# ==============================================================================

# Third Party -----
from fastapi import APIRouter

# Astral AI ----
from app.services.config_service import config_service
from app.services.url_service import UrlService

# ==============================================================================
# Router definition
# ==============================================================================

router = APIRouter(prefix="/api/v1", tags=["urls"])

@router.get("/sites")
def list_sites():
    """List all available sites from yaml.config"""
    sites = config_service.all_sites
    
    return {
        site_id: {
            "name": site_info.name,
            "url": site_info.url,
            "sitemap_url": site_info.sitemap_url,
            "is_sitemap_index": site_info.is_sitemap_index
        }
        for site_id, site_info in sites.items()
    }

@router.post("/trigger/{site_id}")
async def extract_urls(site_id: str):
    """Extracts URLs from a given site (or all)"""
    # Validate site_id using existing config_service
    if site_id != "all" and not config_service.site(site_id):
        return { 
            "error": f"Site {site_id} not found in configuration. If you would like to add it, please add to sites.yaml. See other site configuration or sites_example.yaml for reference." 
        }

    # Initialize service
    url_service = UrlService()
    
    try:
        if site_id == "all":
            # Process all sites using existing config_service
            sites = config_service.all_sites
            results = {}
            for site_id in sites:
                try:
                    results[site_id] = await url_service.process_site(site_id)
                except Exception as e:
                    results[site_id] = {"error": str(e)}
            return results
        else:
            # Process single site
            result = await url_service.process_site(site_id)
            return result
            
    except Exception as e:
        return {"error": f"Processing failed: {str(e)}"}
