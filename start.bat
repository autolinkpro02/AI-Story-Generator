@echo off
rem Start the local web UI (Windows)
pushd %~dp0
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo Warning: virtual environment not found. Run install_windows.ps1 first.
)
echo Starting web app on http://127.0.0.1:8000
python -u web_app.py
popd
