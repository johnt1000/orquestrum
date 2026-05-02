from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ui.lib import doc_loader

router = APIRouter()


@router.get('/coverage', response_class=HTMLResponse)
async def show(request: Request) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates

    coverage_md = cfg.root / 'docs' / 'governance' / 'COVERAGE.md'
    html = ''
    found = coverage_md.is_file()
    if found:
        html = doc_loader.render_markdown(coverage_md.read_text(encoding='utf-8'))
    return templates.TemplateResponse(
        request,
        'coverage.html',
        {'found': found, 'html': html, 'path': str(coverage_md)},
    )
