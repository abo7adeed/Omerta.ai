@echo off
echo ===================================================
echo   Omerta.ai - Starting Langfuse Observability Server
echo ===================================================
echo.
echo Checking Docker engine status...
docker ps >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Docker Desktop is not running yet.
    echo Please launch "Docker Desktop" from your Start Menu,
    echo wait until it finishes starting, and run this file again.
    echo.
    pause
    exit /b 1
)

echo [*] Starting Langfuse Server and PostgreSQL containers...
docker compose -f docker-compose.langfuse.yml up -d

echo.
echo ===================================================
echo [SUCCESS] Langfuse is running!
echo Access the dashboard at: http://localhost:3000
echo ===================================================
echo.
pause

