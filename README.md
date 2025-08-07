# Simplified version of [astral-aggregator](https://github.com/cameronbrady1527/astral-aggregator)

## File Structure

```
aggregator-v2/
├── app/
│   ├── __init__.py
│   ├── main.py                    # fastapi app initialization & config
│   ├── ai/                        # ai functions with prompts and context
│   │   ├── __init__.py
│   │   ├── url_judge.py           # main ai function for url analysis
│   │   └── config.py              # AI prompts and configurations
│   ├── clients/                   # Simple API wrappers
│   │   ├── __init__.py
│   │   ├── firecrawl_client.py    # firecrawl api client
│   │   ├── openai_client.py       # openai api client
│   │   └── ...                    # future api clients
│   ├── crawler/                   # crawling-related functionality
│   │   ├── __init__.py
│   │   └── sitemap_crawler.py     # existing sitemap crawler
│   ├── utils/                     # helper utilities & functions
│   │   ├── __init__.py
│   │   ├── url_utils.py           # url deduplication, normalization, & resolution
│   │   ├── json_writer.py         # manage the writing of json
│   │   ├── excel_exporter.py      # excel export functionality
│   │   └── json_exporter.py       # json export functionality
│   ├── routers/                   # fastapi route definitions
│   │   ├── __init__.py
│   │   └── url_router.py          # all url-related endpoints
│   └── services/                  # business logic layer
│       ├── __init__.py
│       └── url_service.py         # main url processing orchestration
├── config/
│   ├── sites.yaml                 # domain lists and processing info
│   └── sites_example.yaml         # template config
├── scripts/                       # utility scripts
│   ├── __init__.py
│   └── ...
├── output/                        # temporary storage for output url lists
│   ├── judiciary/                 # judiciary output url lists
│   ├── waverley/                  # waverley output url lists
│   └── ...                        # other sites output url lists
├── requirements.txt
├── .env                           # api keys
├── .env.example                   # template for api keys
├── .gitignore
└── README.md
```