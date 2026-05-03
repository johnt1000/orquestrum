"""i18n route — POST /i18n/set persists the locale cookie.

Single endpoint: receives a `lang` form field (`pt` or `en`) and a `next`
URL to redirect back to. Validates `lang` against the supported set;
defaults to `pt` if unknown. Cookie `orq_lang` is HttpOnly + SameSite=Lax,
1-year max-age — local-only console, no need for stricter flags.
"""
from __future__ import annotations
from urllib.parse import urlparse

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from ui.i18n import SUPPORTED, DEFAULT

router = APIRouter()

_COOKIE = 'orq_lang'
_MAX_AGE = 60 * 60 * 24 * 365  # 1 year


def _safe_redirect(target: str | None) -> str:
    """Only allow same-origin redirects (path-only, no scheme/host)."""
    if not target:
        return '/'
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return '/'
    return target if target.startswith('/') else '/'


@router.post('/i18n/set')
async def set_locale(request: Request, lang: str = Form(...), next: str = Form('/')) -> RedirectResponse:
    locale = lang if lang in SUPPORTED else DEFAULT
    target = _safe_redirect(next)
    response = RedirectResponse(url=target, status_code=303)
    response.set_cookie(
        _COOKIE,
        locale,
        max_age=_MAX_AGE,
        httponly=False,  # readable by client JS so the no-FOUC theme script can mirror lang
        samesite='lax',
    )
    return response
