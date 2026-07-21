@echo off
setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo   Build "All for Cabal.exe"  (Item Finder + Create Bundle)
echo ============================================================
echo.

echo [1/4] Checking Python...
where python >nul 2>nul
if errorlevel 1 goto NOPYTHON

echo [2/4] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto FAILDEPS

echo [3/4] Installing Playwright Chromium (fallback browser)...
python -m playwright install chromium

echo [4/4] Building EXE...
pyinstaller --noconfirm all_for_cabal.spec
if errorlevel 1 goto FAILBUILD

echo.
echo ============================================================
echo   DONE!  Output:  dist\All for Cabal.exe
echo ============================================================
start "" explorer dist
goto END

:NOPYTHON
echo.
echo   Python not found. Install from https://www.python.org/downloads/
echo   During install, tick "Add python.exe to PATH".
goto END

:FAILDEPS
echo.
echo   Failed to install dependencies. Check your internet connection.
goto END

:FAILBUILD
echo.
echo   Build failed. See the messages above for details.
goto END

:END
echo.
pause
endlocal
