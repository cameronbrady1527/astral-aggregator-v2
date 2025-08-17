# URL Aggregator v2

A comprehensive web content discovery and monitoring system that automatically discovers, processes, and tracks URLs from various websites using multiple detection methods including sitemaps, AI-powered analysis, and intelligent crawling.

## Overview

The URL Aggregator is designed to solve the challenge of discovering and monitoring content across websites that may not have comprehensive sitemaps or may have content spread across multiple pages. It combines traditional web crawling techniques with AI-powered analysis to identify the most valuable content discovery hubs on any website.

## Key Features

- **Multi-Source URL Discovery**: Combines sitemap parsing, Firecrawl mapping, and intelligent crawling
- **AI-Powered Content Analysis**: Uses OpenAI GPT models to identify the most valuable content discovery URLs
- **Intelligent Deduplication**: Advanced URL resolution and deduplication to eliminate redundant content
- **Comprehensive Monitoring**: Tracks changes and maintains historical URL sets
- **Flexible Configuration**: Per-site configuration for different crawling strategies
- **RESTful API**: FastAPI-based API for integration with other systems
- **Enhanced Pagination Support**: Optional pagination detection for sites with extensive content

## How It Works

### Core Architecture

The system operates through several interconnected components:

1. **URL Discovery Engine**: Discovers URLs from multiple sources (sitemaps, Firecrawl, crawling)
2. **AI Analysis Pipeline**: Analyzes discovered URLs to identify content discovery hubs
3. **Deduplication Engine**: Resolves and deduplicates URLs to create clean, unique sets
4. **Content Monitoring**: Tracks changes and maintains historical data
5. **API Layer**: Provides RESTful endpoints for external integration

### Discovery Process

1. **Sitemap Analysis**: Parses XML sitemaps and sitemap indexes to extract URLs
2. **Firecrawl Mapping**: Uses Firecrawl's map endpoint to discover site structure
3. **AI-Powered Selection**: Analyzes URLs to identify the 5 most valuable content discovery hubs
4. **Content Crawling**: Crawls selected URLs to discover additional content
5. **Deduplication**: Resolves URLs and removes duplicates to create final URL sets

### AI Analysis

The system uses OpenAI GPT models to intelligently analyze URLs and identify:
- Content section pages (news, blog, press releases, etc.)
- Archive or index pages where new content gets added
- Dynamic content aggregators
- Entry points for discovering new content

## File Structure

```
aggregator-v2/
├── app/                               # Main application package
│   ├── __init__.py                    # Package initialization and exports
│   ├── main.py                        # FastAPI application entry point
│   ├── ai/                            # AI configuration and prompts
│   │   ├── __init__.py     
│   │   └── config.py                  # AI model configuration and prompts
│   ├── clients/                       # External API clients
│   │   ├── __init__.py     
│   │   ├── firecrawl_client.py        # Firecrawl SDK integration
│   │   └── openai_client.py           # OpenAI API client
│   ├── crawler/                       # Web crawling functionality
│   │   ├── __init__.py     
│   │   └── sitemap_crawler.py         # Sitemap XML parsing
│   ├── models/                        # Data models and schemas
│   │   ├── __init__.py     
│   │   ├── config_models.py           # Site configuration models
│   │   ├── url_models.py              # URL processing models
│   │   └── pagination_models.py       # Pagination detection models
│   ├── routers/                       # API route definitions
│   │   ├── __init__.py     
│   │   └── url_router.py              # URL processing endpoints
│   ├── services/                      # Business logic layer
│   │   ├── __init__.py     
│   │   ├── config_service.py          # Configuration management
│   │   ├── url_service.py             # Main URL processing orchestration
│   │   ├── pagination_detector.py     # Pagination pattern detection
│   │   ├── pagination_strategies.py   # Pagination handling strategies
│   │   └── content_extractor.py       # Content extraction and classification
│   └── utils/                         # Utility functions
│       ├── __init__.py     
│       ├── url_utils.py               # URL processing utilities
│       ├── json_writer.py             # JSON output management
│       ├── excel_exporter.py          # Excel export functionality
│       ├── json_exporter.py           # JSON export functionality
│       ├── pagination_orchestrator.py # Pagination crawling orchestration
│       └── simple_crawler.py          # HTTP crawling utilities
├── config/                            # Configuration files
│   ├── sites.yaml                     # Site configurations
│   └── sites_example.yaml             # Configuration templates
├── scripts/                           # Utility scripts
│   ├── __init__.py     
│   ├── detect_pagination.py           # Pagination detection utility
│   ├── change_detector.py             # Change detection utility
│   ├── demo_pagination_system.py      # Pagination system demo
│   └── run_demo.py                    # Demo runner
├── docs/                              # Documentation
│   └── INTEGRATION_COMPLETE.md        # Integration guide
├── output/                            # Processing output storage
├── tests/                             # Test suite
├── requirements.txt                   # Python dependencies
├── pyproject.toml                     # Project configuration
├── uv.lock                            # uv dependency lock file
└── README.md                          # You're reading me now!
```

## Quick Start

### 1. Installation

#### Using uv (Recommended)
[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver written in Rust. It's significantly faster than pip and provides better dependency resolution.

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <repository-url>
cd aggregator-v2

# Install dependencies using uv
uv sync

# Activate the virtual environment
uv shell
```

#### Using pip (Alternative)
```bash
# Clone the repository
git clone <repository-url>
cd aggregator-v2

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

```bash
# Set up environment variables
cp .env.example .env
# Edit .env with your API keys:
# - OPENAI_API_KEY=your_openai_key
# - FIRECRAWL_API_KEY=your_firecrawl_key
```

### 3. Configuration

Create or update `config/sites.yaml` with your target sites:

```yaml
sites:
  example_site:
    name: "Example Site"
    url: "https://example.com"
    sitemap_url: "https://example.com/sitemap.xml"
    is_sitemap: true
    is_sitemap_index: false
    onboarded: false
    status: "pending"
    
    # Optional: Pagination configuration
    pagination_enabled: true
    pagination_max_pages: 200
    pagination_rate_limit: 2.0
    pagination_concurrent_batches: 5
```

### 4. Run the System

#### API Mode (Recommended)
```bash
# Start the FastAPI server
uv run uvicorn app.main:app --reload

# Or with pip:
# uvicorn app.main:app --reload

# The API will be available at http://localhost:8000
# API documentation at http://localhost:8000/docs
```

#### Direct Processing via API
```bash
# Process a specific site
curl -X POST http://localhost:8000/api/v1/trigger/example_site

# Process all sites
curl -X POST http://localhost:8000/api/v1/trigger/all

# List configured sites
curl http://localhost:8000/api/v1/sites
```

#### Utility Scripts
```bash
# Analyze a website for pagination patterns
uv run python scripts/detect_pagination.py https://example.com/news

# Analyze a configured site
uv run python scripts/detect_pagination.py --site example_site

# Run pagination demo
uv run python scripts/run_demo.py --quick

# Run full pagination demo
uv run python scripts/run_demo.py --full

# Alternative with pip (if not using uv):
# python scripts/detect_pagination.py https://example.com/news
```

## API Endpoints

### Core Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health status
- `GET /api/v1/sites` - List all configured sites
- `POST /api/v1/trigger/{site_id}` - Process a specific site or all sites using standard processing
- `POST /api/v1/trigger/{site_id}/pagination` - Process a specific site or all sites using pagination-aware processing

### Usage Examples

```bash
# List all sites
curl http://localhost:8000/api/v1/sites

# Process a specific site (standard processing)
curl -X POST http://localhost:8000/api/v1/trigger/example_site

# Process a specific site (with pagination support)
curl -X POST http://localhost:8000/api/v1/trigger/example_site/pagination

# Process all sites (standard processing)
curl -X POST http://localhost:8000/api/v1/trigger/all

# Process all sites (with pagination support)
curl -X POST http://localhost:8000/api/v1/trigger/all/pagination
```

## Configuration

### Site Configuration Options

- **`name`**: Human-readable site name
- **`url`**: Base URL of the site
- **`sitemap_url`**: URL of the site's sitemap (if available)
- **`is_sitemap`**: Whether the site has a sitemap
- **`is_sitemap_index`**: Whether the sitemap is an index file
- **`onboarded`**: Whether the site has been processed before
- **`status`**: Current processing status

### Pagination Configuration (Optional)

- **`pagination_enabled`**: Enable pagination detection and crawling
- **`pagination_max_pages`**: Maximum number of pages to crawl
- **`pagination_rate_limit`**: Seconds between requests
- **`pagination_concurrent_batches`**: Number of concurrent page batches
- **`pagination_custom_patterns`**: Custom pagination patterns

## Use Cases

### Perfect For

- **Content Monitoring**: Track new content across multiple websites
- **SEO Analysis**: Discover all content on a site for optimization
- **Content Discovery**: Find hidden or paginated content
- **Site Auditing**: Comprehensive analysis of website structure
- **Research**: Gather content from multiple sources systematically

### Industries

- **News Organizations**: Monitor competitor content and track industry news
- **Government Agencies**: Monitor policy updates and announcements
- **E-commerce**: Track product updates and competitor offerings
- **Academic Institutions**: Monitor research publications and updates
- **Legal Firms**: Track court decisions and legal updates

## Expected Results

### Typical Output

```
Final URL set contains 2,847 total URLs
Sitemap: 30 URLs
Firecrawl: 15 URLs
AI-Selected Top URLs: 5 URLs
Content Crawling: 2,797 additional URLs
Processing time: 45.8s
```

### What You Get

- **Comprehensive URL Sets**: All discoverable content from target sites
- **Structured Data**: URLs with metadata about discovery method and timing
- **Deduplicated Results**: Clean, unique URL sets with no duplicates
- **Historical Tracking**: Changes tracked over time
- **Export Options**: JSON and Excel output formats

## Advanced Features

### AI-Powered Analysis

The system uses OpenAI GPT models to intelligently analyze URLs and identify the most valuable content discovery hubs. This ensures you're not just getting random URLs, but URLs that will lead to discovering new content.

### Intelligent Deduplication

Advanced URL resolution and deduplication eliminates redundant content:
- URL normalization and resolution
- Duplicate detection across different discovery methods
- Aggressive deduplication for clean results

### Pagination Support

Optional pagination detection for sites with extensive content:
- Automatic pattern detection
- Multiple pagination strategies
- Configurable crawling parameters
- Respectful rate limiting

## Performance Considerations

- **Processing Time**: 2x-5x increase with pagination enabled
- **Memory Usage**: Moderate increase (configurable via batch sizes)
- **Network Usage**: Higher with pagination (respectful rate limiting applied)
- **API Limits**: Respects OpenAI and Firecrawl rate limits

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure all API keys are properly set in `.env`
2. **Rate Limiting**: Adjust pagination settings for large sites
3. **Memory Issues**: Reduce concurrent batch sizes for very large sites
4. **Detection Failures**: Use the pagination detection script to analyze site structure

### Getting Help

- **API Issues**: Check the FastAPI docs at `/docs`
- **Configuration**: Review `sites_example.yaml` for examples
- **Pagination**: Use `scripts/detect_pagination.py` to analyze sites
- **Demo**: Use `scripts/run_demo.py` to test pagination features
- **Logs**: Check console output for detailed processing information

## Development

### Running Tests

```bash
# Run all tests with uv
uv run pytest

# Run specific test file
uv run pytest tests/test_integration.py -v

# Alternative with pip:
# python -m pytest
# python -m pytest tests/test_integration.py -v
```

### Adding New Features

1. **Models**: Add new data models in `app/models/`
2. **Services**: Implement business logic in `app/services/`
3. **API**: Add new endpoints in `app/routers/`
4. **Utilities**: Create helper functions in `app/utils/`

### Dependency Management

#### Adding New Dependencies
```bash
# Using uv (recommended)
uv add package_name

# Using pip
pip install package_name
pip freeze > requirements.txt
```

#### Updating Dependencies
```bash
# Using uv
uv sync --upgrade

# Using pip
pip install --upgrade -r requirements.txt
```

## Dependencies

- **FastAPI**: Modern web framework for APIs
- **OpenAI**: AI-powered URL analysis
- **Firecrawl**: Web crawling and mapping
- **Pydantic**: Data validation and serialization
- **aiohttp**: Asynchronous HTTP client
- **BeautifulSoup**: HTML parsing
- **PyYAML**: Configuration file parsing

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

---

**Ready to discover comprehensive content across the web? The URL Aggregator provides intelligent, AI-powered content discovery with advanced deduplication and monitoring capabilities.**