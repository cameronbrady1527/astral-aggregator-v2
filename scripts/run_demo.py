#!/usr/bin/env python3
# ==============================================================================
# run_demo.py — Simple Demo Runner
# ==============================================================================
# Purpose: Easy-to-use demo runner for the pagination system
# ==============================================================================

"""
🚀 Pagination System Demo Runner

This script provides an easy way to see our pagination system in action.
Choose from different demo options to explore the system's capabilities.

Usage:
    python run_demo.py                    # Interactive menu
    python run_demo.py --quick           # Quick GOV.UK demo
    python run_demo.py --full            # Full comprehensive demo
    python run_demo.py --test            # Run system tests
"""

import sys
import os
import asyncio
import time

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def print_banner():
    """Print the demo banner."""
    print("=" * 80)
    print("🚀 UNIVERSAL PAGINATION DETECTION & CRAWLING SYSTEM")
    print("=" * 80)
    print("This demo showcases our intelligent pagination handling system")
    print("that can automatically detect and crawl any type of paginated website.")
    print("=" * 80)

def print_menu():
    """Print the interactive menu."""
    print("\n🎯 Choose a Demo Option:")
    print("1. 🚀 Quick Demo (GOV.UK News - 5 minutes)")
    print("2. 🔍 Full Demo (All features - 15 minutes)")
    print("3. 🧪 System Tests (Component testing)")
    print("4. 📖 Show Documentation")
    print("5. ❌ Exit")
    print("\n💡 Tip: For first-time users, start with option 1 (Quick Demo)")

def run_quick_demo():
    """Run the quick demo."""
    print("\n🚀 Starting Quick Demo...")
    print("This will demonstrate GOV.UK News pagination (limited to 10 pages)")
    
    try:
        # Import and run quick demo
        from demo_pagination_system import run_quick_demo
        run_quick_demo()
        print("\n✅ Quick demo completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Quick demo failed: {str(e)}")
        print("💡 Make sure you have the required dependencies installed:")
        print("   pip install aiohttp requests beautifulsoup4 pydantic")

def run_full_demo():
    """Run the full demo."""
    print("\n🔍 Starting Full Demo...")
    print("This comprehensive demo will showcase all system features")
    print("Estimated time: 15-20 minutes")
    
    try:
        # Import and run full demo
        from demo_pagination_system import run_full_demo
        asyncio.run(run_full_demo())
        print("\n✅ Full demo completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Full demo failed: {str(e)}")
        print("💡 Make sure you have the required dependencies installed:")
        print("   pip install aiohttp requests beautifulsoup4 pydantic")

def run_system_tests():
    """Run the system tests."""
    print("\n🧪 Running System Tests...")
    print("Testing individual components and integration")
    
    try:
        # Import and run tests
        from test_pagination_system import run_all_tests
        asyncio.run(run_all_tests())
        print("\n✅ System tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ System tests failed: {str(e)}")
        print("💡 Make sure you have the required dependencies installed:")
        print("   pip install aiohttp requests beautifulsoup4 pydantic")

def show_documentation():
    """Show documentation information."""
    print("\n📖 Documentation & Resources")
    print("=" * 50)
    
    docs = [
        ("DEMO_README.md", "Comprehensive demo guide and usage instructions"),
        ("PAGINATION_SYSTEM_DEMO_REPORT.md", "Generated demo report (after running full demo)"),
        ("app/models/pagination_models.py", "Data models and structures"),
        ("app/utils/pagination_detector.py", "Pagination detection engine"),
        ("app/utils/pagination_strategies.py", "Pagination strategy implementations"),
        ("app/utils/pagination_orchestrator.py", "Main orchestration system"),
        ("app/utils/simple_crawler.py", "HTTP crawling utilities"),
        ("config/sites_example.yaml", "Example site configurations")
    ]
    
    for filename, description in docs:
        if os.path.exists(filename):
            print(f"✅ {filename}")
            print(f"   {description}")
        else:
            print(f"❌ {filename} (not found)")
    
    print("\n💡 To view a file:")
    print(f"   cat {docs[0][0]}  # View demo README")
    print(f"   less {docs[0][0]}  # View with pager")

def check_dependencies():
    """Check if required dependencies are available."""
    print("\n🔍 Checking Dependencies...")
    
    dependencies = [
        ("aiohttp", "Async HTTP client"),
        ("requests", "HTTP client library"),
        ("beautifulsoup4", "HTML parsing"),
        ("pydantic", "Data validation")
    ]
    
    missing = []
    for dep, description in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep} - {description}")
        except ImportError:
            print(f"❌ {dep} - {description} (MISSING)")
            missing.append(dep)
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print("💡 Install them with:")
        print(f"   pip install {' '.join(missing)}")
        print("\nOr use the project's dependency manager:")
        print("   uv sync")
        return False
    
    print("\n✅ All dependencies are available!")
    return True

def interactive_menu():
    """Run the interactive menu."""
    while True:
        print_menu()
        
        try:
            choice = input("\n🎯 Enter your choice (1-5): ").strip()
            
            if choice == "1":
                if check_dependencies():
                    run_quick_demo()
                else:
                    print("\n❌ Please install missing dependencies first.")
            elif choice == "2":
                if check_dependencies():
                    run_full_demo()
                else:
                    print("\n❌ Please install missing dependencies first.")
            elif choice == "3":
                if check_dependencies():
                    run_system_tests()
                else:
                    print("\n❌ Please install missing dependencies first.")
            elif choice == "4":
                show_documentation()
            elif choice == "5":
                print("\n👋 Thanks for exploring our pagination system!")
                print("🚀 Ready to transform your crawling capabilities!")
                break
            else:
                print("\n❌ Invalid choice. Please enter 1-5.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Demo interrupted. Thanks for exploring!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
        
        # Brief pause between operations
        if choice in ["1", "2", "3"]:
            input("\n⏸️  Press Enter to continue...")

def main():
    """Main entry point."""
    print_banner()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ["--quick", "-q"]:
            if check_dependencies():
                run_quick_demo()
            else:
                print("\n❌ Please install missing dependencies first.")
                sys.exit(1)
        elif arg in ["--full", "-f"]:
            if check_dependencies():
                run_full_demo()
            else:
                print("\n❌ Please install missing dependencies first.")
                sys.exit(1)
        elif arg in ["--test", "-t"]:
            if check_dependencies():
                run_system_tests()
            else:
                print("\n❌ Please install missing dependencies first.")
                sys.exit(1)
        elif arg in ["--help", "-h"]:
            print(__doc__)
            return
        else:
            print(f"❌ Unknown argument: {arg}")
            print("Use --help for usage information")
            sys.exit(1)
    else:
        # No arguments, run interactive menu
        interactive_menu()

if __name__ == "__main__":
    main()
