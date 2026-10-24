"""
FastAPI Application for MorphAPI V2
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from morphapi_v2.api.routes import router as v2_router
from morphapi_v2.demo.mock_store import render_mock_store_html, set_mode
from morphapi_v2.observability.correlation import CorrelationIdMiddlewareV2
from morphapi_v2.observability.logging import RequestLoggingMiddlewareV2, setup_logging_v2

# Initialize V2 structured logging
logger = setup_logging_v2()

app = FastAPI(
    title="MorphAPI V2 Gateway",
    description="Next-generation generalized Web-to-API and MCP gateway with DOM cluster analysis and network sniffing",
    version="2.0.0",
)

# Middleware ordering: RequestLogging wraps CorrelationId, which wraps CORS
app.add_middleware(RequestLoggingMiddlewareV2)
app.add_middleware(CorrelationIdMiddlewareV2)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v2_router)


@app.get("/mock-store", response_class=HTMLResponse)
@app.get("/demo/mock-store", response_class=HTMLResponse)
async def mock_store_root(mode: str | None = None):
    if mode:
        set_mode(mode)
    return render_mock_store_html(mode)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("morphapi_v2.api.app:app", host="0.0.0.0", port=8001, reload=True)
