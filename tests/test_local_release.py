from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from local_app.release_verify import verify_tree, write_checksum


ROOT = Path(__file__).resolve().parents[1]


def test_release_verifier_rejects_private_runtime_files(tmp_path):
    package = tmp_path / 'package'
    package.mkdir()
    (package / 'web').mkdir()
    (package / 'web' / 'app.py').write_text('safe', encoding='utf-8')
    (package / 'all_for_cabal_web.db').write_bytes(b'private')

    with pytest.raises(ValueError, match='all_for_cabal_web.db'):
        verify_tree(package)


@pytest.mark.parametrize(
    'relative_path',
    [
        '.ENV',
        'CONFIG.JSON',
        'data/private.SQLite3',
        'uploads/plan.XLSM',
        '__pycache__/module.pyc',
        'nested/.git/config',
        'nested/build/output.bin',
        'nested/.cabal_chrome_profile/Default/Cookies',
    ],
)
def test_release_verifier_is_case_insensitive_and_checks_every_component(
    tmp_path, relative_path
):
    package = tmp_path / 'package'
    target = package / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b'private')

    with pytest.raises(ValueError, match=target.name):
        verify_tree(package)


def test_release_verifier_accepts_app_and_writes_sha256(tmp_path):
    package = tmp_path / 'package'
    package.mkdir()
    executable = package / 'All for Cabal Web.exe'
    executable.write_bytes(b'installer')

    verify_tree(package)
    checksum = write_checksum(executable)

    expected = hashlib.sha256(b'installer').hexdigest()
    assert checksum.name == 'All for Cabal Web.exe.sha256'
    assert checksum.read_text(encoding='ascii') == (
        f'{expected} *All for Cabal Web.exe\n'
    )


def test_pyinstaller_spec_is_one_directory_and_bundles_offline_assets():
    spec = (ROOT / 'local_web.spec').read_text(encoding='utf-8')

    assert "['local_app/launcher.py']" in spec
    assert 'console=False' in spec
    assert 'COLLECT(' in spec
    for fragment in (
        'web/static',
        'alembic.ini',
        'build-cache',
        'ms-playwright',
        'pyinstaller_runtime_hook.py',
        "'fastapi'",
        "'uvicorn.logging'",
        "'sqlalchemy.dialects.sqlite.pysqlite'",
        "'alembic.runtime.migration'",
        "'cryptography.hazmat.primitives.ciphers.aead'",
        "'argon2'",
        "'openpyxl.worksheet._reader'",
        "'playwright.async_api'",
    ):
        assert fragment in spec


def test_installer_contract_preserves_local_data_and_starts_launcher():
    installer = (
        ROOT / 'installer' / 'AllForCabalWeb.iss'
    ).read_text(encoding='utf-8')

    for fragment in (
        'AppId={{6B5A3461-9A4C-4D08-A72A-6F7426F22C91}',
        'ArchitecturesAllowed=x64compatible',
        'ArchitecturesInstallIn64BitMode=x64compatible',
        'PrivilegesRequired=lowest',
        'All for Cabal Web.exe',
        'postinstall',
        'desktopicon',
    ):
        assert fragment in installer
    assert '[UninstallDelete]' not in installer
    assert 'AllForCabalWeb' not in installer.split('[Files]', 1)[-1]


def test_build_script_installs_browser_runs_tests_and_verifies_release():
    script = (
        ROOT / 'scripts' / 'build_local_installer.ps1'
    ).read_text(encoding='utf-8')

    for fragment in (
        "$ErrorActionPreference = 'Stop'",
        'requirements-build.txt',
        'PLAYWRIGHT_BROWSERS_PATH',
        'playwright install chromium',
        'python -m pytest -q',
        'python -m PyInstaller',
        'local_app.release_verify',
        'ISCC.exe',
        'LOCALAPPDATA',
    ):
        assert fragment in script
