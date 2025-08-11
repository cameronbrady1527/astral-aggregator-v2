#!/usr/bin/env python3
"""
Simple test script to test core functionality without full app imports.
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

async def test_basic_functionality():
    """Test basic functionality without full app stack."""
    print("🚀 Testing basic functionality...")
    
    try:
        # Test if we can import the basic models
        from models.url_models import UrlInfo, DetectionMethod, UrlSet, ProcessingSummary
        print("✅ Basic models imported successfully")
        
        # Test if we can create basic objects
        url_info = UrlInfo(
            url="https://example.com",
            detection_methods=[DetectionMethod.SITEMAP],
            detected_at=asyncio.get_event_loop().time()
        )
        print("✅ UrlInfo created successfully")
        
        # Test if we can create a UrlSet
        url_set = UrlSet(
            site_id="test_site",
            timestamp=asyncio.get_event_loop().time(),
            urls=[url_info],
            total_count=1
        )
        print("✅ UrlSet created successfully")
        
        # Test if we can serialize to dict
        url_set_dict = url_set.model_dump()
        print("✅ UrlSet serialized successfully")
        
        # Test if we can import JsonWriter
        from utils.json_writer import JsonWriter
        print("✅ JsonWriter imported successfully")
        
        # Test if we can create JsonWriter
        writer = JsonWriter()
        print("✅ JsonWriter created successfully")
        
        print("✅ All basic functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_basic_functionality())
