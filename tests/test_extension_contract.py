from __future__ import annotations

import json
from pathlib import Path

EXTENSION = Path(__file__).resolve().parents[1] / 'extension'

AZTEK_HOST = 'aztek-tools.combo-interactive.com'
AZTEK_ORIGIN = 'https://aztek-tools.combo-interactive.com'


def read(name: str) -> str:
    return (EXTENSION / name).read_text('utf-8')


def test_extension_permissions_are_scoped_to_aztek():
    manifest = json.loads(read('manifest.json'))
    assert manifest['manifest_version'] == 3
    assert 'cookies' in manifest['permissions']
    assert manifest['host_permissions'] == [
        AZTEK_ORIGIN + '/*',
        'http://localhost:8000/*',
    ]


def test_content_scripts_only_target_the_aztek_host():
    manifest = json.loads(read('manifest.json'))
    for entry in manifest.get('content_scripts', []):
        for match in entry['matches']:
            assert AZTEK_HOST in match
            assert 'localhost' not in match


def test_extension_posts_pairing_payload_without_password():
    source = read('popup.js')
    assert '/api/aztek/pair' in source
    assert 'storage_state' in source
    assert 'pairing_token' in source
    assert 'password' not in source.casefold()


def test_popup_reads_cookies_only_from_the_aztek_host():
    source = read('popup.js')
    assert AZTEK_HOST in source
    assert 'chrome.cookies.getAll' in source


def test_config_exposes_only_a_backend_origin_and_no_secret():
    source = read('config.js')
    assert 'BACKEND_ORIGIN' in source
    lowered = source.casefold()
    for secret in ('password', 'secret', 'token', 'api_key', 'apikey'):
        assert secret not in lowered


def test_popup_never_injects_untrusted_html():
    source = read('popup.js')
    assert '.innerHTML' not in source
    assert 'textContent' in source


def test_install_documentation_exists():
    doc = (EXTENSION.parent / 'docs' / 'install-extension.md').read_text('utf-8')
    assert 'chrome://extensions' in doc
    assert 'BACKEND_ORIGIN' in doc
