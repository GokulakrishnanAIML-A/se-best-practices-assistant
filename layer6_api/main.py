"""Main FastAPI Application Entry Point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from layer6_api.routes import review

app = FastAPI(
    title="SE Best Practices Assistant API",
    description="Agentic code review assistant grounding findings in software engineering best practices.",
    version="1.0.0",
)

# Enable CORS for Streamlit and web frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Session-Id"],
)

# Register routers
app.include_router(review.router)


@app.get("/", tags=["System"])
async def root() -> dict[str, str]:
    """Root endpoint providing service metadata and link to docs."""
    return {
        "message": "SE Best Practices Assistant API is running.",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for container probes and load balancers."""
    return {"status": "ok", "service": "SE Best Practices Assistant API"}

