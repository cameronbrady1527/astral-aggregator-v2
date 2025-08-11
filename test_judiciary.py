#!/usr/bin/env python3
"""
Test script to run Judiciary site processing and check if saving works.
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from services.url_service import UrlService

async def main():
    """Test the Judiciary site processing."""
    print("🚀 Testing Judiciary site processing...")
    
    try:
        # Create URL service
        url_service = UrlService()
        
        # Process the Judiciary site
        result = await url_service.process_site("judiciary_uk")
        
        print(f"✅ Processing complete!")
        print(f"📊 Result: {result}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
