@echo off
REM ========================================
REM Docker Image Build Script (Windows)
REM ========================================
REM ShopFDS Platform - Build all Docker images
REM
REM Usage:
REM   build-images.bat [VERSION]
REM
REM Examples:
REM   build-images.bat         REM Build with 'latest' tag
REM   build-images.bat v1.2.0  REM Build with specific version tag
REM ========================================

setlocal enabledelayedexpansion

REM Configuration
set "REGISTRY=shopfds"
set "VERSION=%~1"
if "%VERSION%"=="" set "VERSION=latest"

REM Get current directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\..\"

REM Git commit hash
for /f "delims=" %%i in ('git rev-parse --short HEAD 2^>nul') do set "GIT_COMMIT=%%i"
if "%GIT_COMMIT%"=="" set "GIT_COMMIT=unknown"

REM Build date (ISO 8601)
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set "datetime=%%I"
set "BUILD_DATE=%datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2%T%datetime:~8,2%:%datetime:~10,2%:%datetime:~12,2%Z"

echo ==========================================
echo ShopFDS Docker Image Build
echo ==========================================
echo Registry:    %REGISTRY%
echo Version:     %VERSION%
echo Build Date:  %BUILD_DATE%
echo Git Commit:  %GIT_COMMIT%
echo ==========================================
echo.

REM Track failed builds
set "FAILED_BUILDS="

REM ========================================
REM Build Backend Services
REM ========================================

echo ==========================================
echo Building Backend Services
echo ==========================================
echo.

REM Ecommerce Backend
echo [BUILD] Building ecommerce-backend...
docker build ^
    --tag "%REGISTRY%/ecommerce-backend:%VERSION%" ^
    --tag "%REGISTRY%/ecommerce-backend:latest" ^
    --label "version=%VERSION%" ^
    --label "build-date=%BUILD_DATE%" ^
    --label "git-commit=%GIT_COMMIT%" ^
    --file "%PROJECT_ROOT%services\ecommerce\backend\Dockerfile" ^
    "%PROJECT_ROOT%services\ecommerce\backend"
if errorlevel 1 (
    echo [FAIL] Failed to build ecommerce-backend
    set "FAILED_BUILDS=!FAILED_BUILDS! ecommerce-backend"
) else (
    echo [OK] ecommerce-backend built successfully
)
echo.

REM FDS Service
echo [BUILD] Building fds-service...
docker build ^
    --tag "%REGISTRY%/fds-service:%VERSION%" ^
    --tag "%REGISTRY%/fds-service:latest" ^
    --label "version=%VERSION%" ^
    --label "build-date=%BUILD_DATE%" ^
    --label "git-commit=%GIT_COMMIT%" ^
    --file "%PROJECT_ROOT%services\fds\Dockerfile" ^
    "%PROJECT_ROOT%services\fds"
if errorlevel 1 (
    echo [FAIL] Failed to build fds-service
    set "FAILED_BUILDS=!FAILED_BUILDS! fds-service"
) else (
    echo [OK] fds-service built successfully
)
echo.

REM ML Service
echo [BUILD] Building ml-service...
docker build ^
    --tag "%REGISTRY%/ml-service:%VERSION%" ^
    --tag "%REGISTRY%/ml-service:latest" ^
    --label "version=%VERSION%" ^
    --label "build-date=%BUILD_DATE%" ^
    --label "git-commit=%GIT_COMMIT%" ^
    --file "%PROJECT_ROOT%services\ml-service\Dockerfile" ^
    "%PROJECT_ROOT%services\ml-service"
if errorlevel 1 (
    echo [FAIL] Failed to build ml-service
    set "FAILED_BUILDS=!FAILED_BUILDS! ml-service"
) else (
    echo [OK] ml-service built successfully
)
echo.

REM Admin Dashboard Backend
echo [BUILD] Building admin-dashboard-backend...
docker build ^
    --tag "%REGISTRY%/admin-dashboard-backend:%VERSION%" ^
    --tag "%REGISTRY%/admin-dashboard-backend:latest" ^
    --label "version=%VERSION%" ^
    --label "build-date=%BUILD_DATE%" ^
    --label "git-commit=%GIT_COMMIT%" ^
    --file "%PROJECT_ROOT%services\admin-dashboard\backend\Dockerfile" ^
    "%PROJECT_ROOT%services\admin-dashboard\backend"
if errorlevel 1 (
    echo [FAIL] Failed to build admin-dashboard-backend
    set "FAILED_BUILDS=!FAILED_BUILDS! admin-dashboard-backend"
) else (
    echo [OK] admin-dashboard-backend built successfully
)
echo.

REM ========================================
REM Build Frontend Services
REM ========================================

echo ==========================================
echo Building Frontend Services
echo ==========================================
echo.

REM Ecommerce Frontend
echo [BUILD] Building ecommerce-frontend...
docker build ^
    --tag "%REGISTRY%/ecommerce-frontend:%VERSION%" ^
    --tag "%REGISTRY%/ecommerce-frontend:latest" ^
    --label "version=%VERSION%" ^
    --label "build-date=%BUILD_DATE%" ^
    --label "git-commit=%GIT_COMMIT%" ^
    --file "%PROJECT_ROOT%services\ecommerce\frontend\Dockerfile" ^
    "%PROJECT_ROOT%services\ecommerce\frontend"
if errorlevel 1 (
    echo [FAIL] Failed to build ecommerce-frontend
    set "FAILED_BUILDS=!FAILED_BUILDS! ecommerce-frontend"
) else (
    echo [OK] ecommerce-frontend built successfully
)
echo.

REM Admin Dashboard Frontend
echo [BUILD] Building admin-dashboard-frontend...
docker build ^
    --tag "%REGISTRY%/admin-dashboard-frontend:%VERSION%" ^
    --tag "%REGISTRY%/admin-dashboard-frontend:latest" ^
    --label "version=%VERSION%" ^
    --label "build-date=%BUILD_DATE%" ^
    --label "git-commit=%GIT_COMMIT%" ^
    --file "%PROJECT_ROOT%services\admin-dashboard\frontend\Dockerfile" ^
    "%PROJECT_ROOT%services\admin-dashboard\frontend"
if errorlevel 1 (
    echo [FAIL] Failed to build admin-dashboard-frontend
    set "FAILED_BUILDS=!FAILED_BUILDS! admin-dashboard-frontend"
) else (
    echo [OK] admin-dashboard-frontend built successfully
)
echo.

REM ========================================
REM Build Summary
REM ========================================

echo.
echo ==========================================
echo Build Summary
echo ==========================================

if "%FAILED_BUILDS%"=="" (
    echo [SUCCESS] All images built successfully!
    echo.
    echo Built images:
    docker images --filter "label=version=%VERSION%"
    echo.
    echo Next steps:
    echo   1. Test images locally: docker-compose -f docker-compose.prod.yml up -d
    echo   2. Push to registry: push-images.bat %VERSION%
    echo   3. Deploy to Kubernetes: kubectl apply -k infrastructure/k8s/
    exit /b 0
) else (
    echo [FAIL] Failed to build the following images:
    echo !FAILED_BUILDS!
    echo.
    echo Please check the error messages above and fix the issues.
    exit /b 1
)
