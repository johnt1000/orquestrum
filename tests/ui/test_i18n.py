"""Tests for the i18n layer: dict lookup, locale middleware, /i18n/set route."""
from __future__ import annotations
from pathlib import Path

import httpx
import pytest

from ui.config import UIConfig
from ui.i18n import DEFAULT, FALLBACK, SUPPORTED, resolve, translate
from ui.server import LOCALE_COOKIE, create_app


@pytest.fixture()
def project_config(tmp_path: Path) -> UIConfig:
    return UIConfig(
        mode='project',
        root=tmp_path,
        metrics_dir=tmp_path / '.orquestrum' / 'metrics',
        targets_path=None,
        port=7700,
    )


@pytest.fixture()
async def client(project_config: UIConfig) -> httpx.AsyncClient:
    app = create_app(project_config)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://test',
    ) as c:
        yield c


# ─── translate() / resolve() ────────────────────────────────────────────────

class TestTranslate:
    def test_pt_lookup_returns_portuguese(self):
        assert translate('nav.overview', locale='pt') == 'Visão geral'

    def test_en_lookup_returns_english(self):
        assert translate('nav.overview', locale='en') == 'Overview'

    def test_unknown_locale_falls_back_to_default(self):
        # Unknown locales aren't supported by translate directly; resolve coerces them.
        assert resolve('xx') == DEFAULT
        assert resolve('pt') == 'pt'
        assert resolve('en') == 'en'

    def test_missing_key_falls_back_to_english(self, tmp_path, monkeypatch):
        # If a key exists in EN but not in PT, PT lookup should return the EN string.
        from ui import i18n as i18n_mod
        # Force-load: en has 'nav.overview'; ensure if PT entry is None, we use EN.
        # We can't easily delete a real key without mutating files, so verify via known fallback path:
        # add a synthetic key only to en at runtime via cache poisoning.
        i18n_mod.load.cache_clear()
        en = dict(i18n_mod.load('en'))
        en['only.in.en'] = 'EN only'
        monkeypatch.setattr(i18n_mod, 'load', lambda loc: en if loc == 'en' else {})
        assert translate('only.in.en', locale='pt') == 'EN only'

    def test_unknown_key_returns_key_itself(self):
        assert translate('totally.unknown.key', locale='pt') == 'totally.unknown.key'

    def test_format_vars_interpolated(self):
        # 'brand.subtitle' = 'console v{version}' (both locales)
        assert translate('brand.subtitle', locale='pt', version='9.9.9') == 'console v9.9.9'
        assert translate('brand.subtitle', locale='en', version='9.9.9') == 'console v9.9.9'

    def test_supported_locales_documented(self):
        assert 'pt' in SUPPORTED
        assert 'en' in SUPPORTED
        assert DEFAULT == 'pt'
        assert FALLBACK == 'en'


# ─── locale middleware + cookie ─────────────────────────────────────────────

class TestLocaleCookie:
    async def test_default_locale_when_no_cookie(self, client: httpx.AsyncClient):
        r = await client.get('/dashboard')
        assert r.status_code == 200
        # Default PT — sidebar should render PT label (no need to hit every label, one is enough)
        assert 'Visão geral' in r.text

    async def test_explicit_pt_cookie_renders_pt(self, client: httpx.AsyncClient):
        r = await client.get('/dashboard', cookies={LOCALE_COOKIE: 'pt'})
        assert 'Visão geral' in r.text

    async def test_explicit_en_cookie_renders_en(self, client: httpx.AsyncClient):
        r = await client.get('/dashboard', cookies={LOCALE_COOKIE: 'en'})
        assert 'Overview' in r.text

    async def test_invalid_cookie_falls_back_to_pt(self, client: httpx.AsyncClient):
        r = await client.get('/dashboard', cookies={LOCALE_COOKIE: 'xx-bogus'})
        assert 'Visão geral' in r.text


# ─── /i18n/set ──────────────────────────────────────────────────────────────

class TestI18nSetRoute:
    async def test_post_sets_cookie_and_redirects(self, client: httpx.AsyncClient):
        r = await client.post(
            '/i18n/set',
            data={'lang': 'en', 'next': '/dashboard'},
            follow_redirects=False,
        )
        assert r.status_code == 303
        assert r.headers['location'] == '/dashboard'
        assert r.cookies.get(LOCALE_COOKIE) == 'en'

    async def test_post_unknown_lang_coerces_to_default(self, client: httpx.AsyncClient):
        r = await client.post(
            '/i18n/set',
            data={'lang': 'xx', 'next': '/'},
            follow_redirects=False,
        )
        assert r.cookies.get(LOCALE_COOKIE) == 'pt'

    async def test_post_rejects_external_redirect(self, client: httpx.AsyncClient):
        r = await client.post(
            '/i18n/set',
            data={'lang': 'pt', 'next': 'https://evil.example.com/x'},
            follow_redirects=False,
        )
        assert r.headers['location'] == '/'

    async def test_post_rejects_protocol_relative_redirect(self, client: httpx.AsyncClient):
        r = await client.post(
            '/i18n/set',
            data={'lang': 'pt', 'next': '//evil.example.com/x'},
            follow_redirects=False,
        )
        # Path doesn't start with single '/', so safe_redirect coerces to '/'
        assert r.headers['location'] == '/'

    async def test_locale_persists_across_requests(self, client: httpx.AsyncClient):
        await client.post('/i18n/set', data={'lang': 'en', 'next': '/'}, follow_redirects=False)
        r = await client.get('/dashboard')
        assert 'Overview' in r.text
        assert 'Visão geral' not in r.text


# ─── theme + i18n shell wiring ──────────────────────────────────────────────

class TestShellWiring:
    async def test_data_theme_attribute_present(self, client: httpx.AsyncClient):
        r = await client.get('/dashboard')
        assert 'data-theme=' in r.text

    async def test_no_fouc_script_present(self, client: httpx.AsyncClient):
        r = await client.get('/dashboard')
        assert 'orq-theme' in r.text  # localStorage key from the inline pre-CSS script

    async def test_lang_switch_form_present(self, client: httpx.AsyncClient):
        r = await client.get('/dashboard')
        assert 'action="/i18n/set"' in r.text

    async def test_segmented_theme_toggle_present(self, client: httpx.AsyncClient):
        r = await client.get('/dashboard')
        assert 'data-theme-pref="auto"'  in r.text
        assert 'data-theme-pref="light"' in r.text
        assert 'data-theme-pref="dark"'  in r.text
