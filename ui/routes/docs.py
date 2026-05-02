from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from ui.lib import doc_loader

router = APIRouter(prefix='/docs')


@router.get('', response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    docs = doc_loader.list_docs(cfg.root)
    by_audience: dict[str, list] = {'agent-context': [], 'governance': [], 'baselines': [], 'other': []}
    for d in docs:
        by_audience[d.audience].append(d)
    return templates.TemplateResponse(
        request,
        'doc_index.html',
        {'by_audience': by_audience, 'badges': doc_loader.AUDIENCE_BADGES},
    )


@router.get('/search', response_class=HTMLResponse)
async def search(request: Request, q: str = Query(default='', max_length=200)) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    hits = doc_loader.search(cfg.root, q) if q else []
    return templates.TemplateResponse(
        request,
        'doc_search.html',
        {'q': q, 'hits': hits},
    )


@router.get('/view', response_class=HTMLResponse)
async def view(request: Request, p: str = Query(..., max_length=300)) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates

    # Path safety: must resolve under cfg.root, must be .md
    target = (cfg.root / p).resolve()
    try:
        target.relative_to(cfg.root)
    except ValueError:
        raise HTTPException(status_code=400, detail='path escapes root')
    if target.suffix != '.md' or not target.is_file():
        raise HTTPException(status_code=404, detail='not a markdown file')

    text = target.read_text(encoding='utf-8')
    html = doc_loader.render_markdown(text)
    rel  = target.relative_to(cfg.root).as_posix()
    return templates.TemplateResponse(
        request,
        'doc_view.html',
        {'rel': rel, 'html': html, 'audience': doc_loader._classify(rel),
         'badges': doc_loader.AUDIENCE_BADGES},
    )
