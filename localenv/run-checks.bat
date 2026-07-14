@echo off
SETLOCAL EnableDelayedExpansion

:: Capture project and repository roots cleanly
SET "LOCALENV_DIR=%~dp0"
cd /d "%LOCALENV_DIR%\..\src\agent"

echo ========================================================================
echo 🚀 Synchronizing Virtual Environment via uv (Python 3.12)
echo ========================================================================
call uv sync --frozen
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo ========================================================================
echo 🚀 Executing Linter Checks (Ruff)
echo ========================================================================
:: Using explicit current directory context prevents OS path resolution bugs
call uv run ruff check .
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo ========================================================================
echo 🚀 Executing Strict Code Quality Type Assertions (MyPy)
echo ========================================================================
call .venv\Scripts\activate.bat

cd /d "%LOCALENV_DIR%\.."
call uv run mypy src/ --strict
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo ========================================================================
echo 🚀 Executing Automated Test Engine Pipeline (PyTest)
echo ========================================================================
set DEPLOYMENT_ENV=test
set PLATFORM_SILVER_BUCKET=mock-local-bucket
set PLATFORM_QUARANTINE_BUCKET=mock-quarantine-bucket
set PYTHONPATH=.
call uv run --python src\agent\.venv\Scripts\python.exe pytest tests/ -v
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo ========================================================================
echo ✅ SUCCESS: Workspace conforms to production standards.
echo ========================================================================
cd /d "%LOCALENV_DIR%\.."