@echo off
REM ========================================
REM ShopFDS Domain Update Script (Windows)
REM ========================================
REM Usage:
REM   update-domain.bat YOUR_DOMAIN
REM
REM Example:
REM   update-domain.bat myshop.com
REM ========================================

setlocal enabledelayedexpansion

REM Check if domain argument is provided
if "%~1"=="" (
    echo [ERROR] Domain not provided!
    echo.
    echo Usage: %~nx0 YOUR_DOMAIN
    echo Example: %~nx0 myshop.com
    exit /b 1
)

set "NEW_DOMAIN=%~1"
set "OLD_DOMAIN=shopfds.example.com"
set "ENV_FILE=.env.production"

REM Check if .env.production exists
if not exist "%ENV_FILE%" (
    echo [ERROR] %ENV_FILE% not found!
    echo Please run this script from infrastructure\docker\ directory
    exit /b 1
)

echo ==========================================
echo ShopFDS Domain Update
echo ==========================================
echo Old Domain: %OLD_DOMAIN%
echo New Domain: %NEW_DOMAIN%
echo File:       %ENV_FILE%
echo ==========================================
echo.

REM Create backup
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set "mydate=%%c%%a%%b")
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set "mytime=%%a%%b")
set "BACKUP_FILE=%ENV_FILE%.backup.%mydate%_%mytime%"
copy "%ENV_FILE%" "%BACKUP_FILE%" >nul
echo [OK] Backup created: %BACKUP_FILE%
echo.

REM Show what will be changed
echo Will update the following lines:
echo ----------------------------------------
findstr /N "%OLD_DOMAIN%" "%ENV_FILE%"
echo ----------------------------------------
echo.

REM Ask for confirmation
set /p REPLY="Continue with replacement? (y/n) "
if /i not "%REPLY%"=="y" (
    echo [CANCELLED] No changes made.
    del "%BACKUP_FILE%"
    exit /b 0
)

REM Perform replacement using PowerShell
powershell -Command "(Get-Content '%ENV_FILE%') -replace '%OLD_DOMAIN%', '%NEW_DOMAIN%' | Set-Content '%ENV_FILE%'"

echo.
echo ==========================================
echo Update Complete!
echo ==========================================
echo [OK] Replaced all occurrences
echo.
echo Updated lines:
echo ----------------------------------------
findstr /N "%NEW_DOMAIN%" "%ENV_FILE%"
echo ----------------------------------------
echo.
echo Next steps:
echo   1. Review changes: notepad %ENV_FILE%
echo   2. Configure DNS for your domain:
echo      - %NEW_DOMAIN%                -^> [Server IP]
echo      - api.%NEW_DOMAIN%            -^> [Server IP]
echo      - fds.%NEW_DOMAIN%            -^> [Server IP]
echo      - ml.%NEW_DOMAIN%             -^> [Server IP]
echo      - admin.%NEW_DOMAIN%          -^> [Server IP]
echo      - admin-api.%NEW_DOMAIN%      -^> [Server IP]
echo   3. Deploy: docker-compose -f docker-compose.prod.yml up -d
echo.
echo Backup saved at: %BACKUP_FILE%
echo ==========================================

endlocal
