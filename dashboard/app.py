import os
import time

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import escape
from typing import Dict, Tuple

from tools.citation_manager import ProductionCitationManager

app = FastAPI()

# Set up templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Mount static files (optional, for CSS/JS)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Simple in-memory cache for citation HTML, keyed by conversation_id
_citation_cache: Dict[str, Tuple[str, float]] = {}
_CACHE_TTL = 60  # seconds

@app.get("/", response_class=HTMLResponse)
def dashboard_home(request: Request) -> HTMLResponse:
    """Render the dashboard home page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/citations/{conversation_id}", response_class=HTMLResponse)
def get_citations(request: Request, conversation_id: str) -> HTMLResponse:
    """HTMX endpoint for dynamic citation loading with simple caching and demo data."""
    now = time.time()
    cache_entry = _citation_cache.get(conversation_id)
    if cache_entry:
        html_citations, timestamp = cache_entry
        if now - timestamp < _CACHE_TTL:
            return HTMLResponse(html_citations)
    citation_mgr = ProductionCitationManager()
    citations = citation_mgr.get_conversation_citations(conversation_id)
    # DEMO: If no citations, add demo data
    if not citations:
        citation_mgr.add_citation(
            url="https://example.com/article1",
            title="Sample Article 1",
            content_preview="This is a sample article for testing...",
            domain="example.com"
        )
        citation_mgr.add_citation(
            url="https://example.com/article2",
            title="Sample Article 2",
            content_preview="Another sample article for testing...",
            domain="example.com"
        )
        citation_mgr.add_citation(
            url="https://example.com/article3",
            title="Sample Article 3",
            content_preview="Third sample article for testing...",
            domain="example.com"
        )
        citations = citation_mgr.get_all_citations()
    html_citations = ""
    for citation in citations:
        safe_url = escape(citation.url)
        safe_title = escape(citation.title)
        html_citations += f'''
        <div class="citation" id="citation-{citation.id}">
            <a href="{safe_url}" target="_blank" rel="noopener noreferrer">
                <sup>{citation.id}</sup> {safe_title}
            </a>
        </div>
        '''
    _citation_cache[conversation_id] = (html_citations, now)
    return HTMLResponse(html_citations)
