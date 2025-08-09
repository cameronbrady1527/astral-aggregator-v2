from fastapi import FastAPI
from app.routers import url_router

app = FastAPI(
    title="URL Aggregator API",
    description="API for extracting and noting changes to URLs from various sites",
    version="1.0.0"
)

# include routers
app.include_router(url_router)

@app.get("/")
def read_root():
    """Health check endpoint"""
    return {"message": "URL Aggregator API is running", "status": "healthy"}

@app.get("/health")
def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "url-aggregator"
    }