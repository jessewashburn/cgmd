@echo off
REM Classical Guitar Music Database - Quick Setup Script (Windows)
REM This script helps complete the Phase 3 setup

echo ===================================
echo CGMD Backend Setup
echo ===================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Error: Virtual environment not found. 
    echo Please run: python -m venv venv
    exit /b 1
)

echo [OK] Virtual environment found
echo.

echo Step 1: Activate virtual environment
echo    Run: venv\Scripts\activate
echo.
pause

REM Check if .env exists
if not exist ".env" (
    echo Warning: .env file not found. Creating from .env.example...
    copy .env.example .env
    echo Please edit .env with your MySQL credentials
    echo.
    pause
)

echo [OK] .env file found
echo.

echo Step 2: Create MySQL database
echo    Run these commands in MySQL:
echo    mysql -u root -p
echo    CREATE DATABASE cgmd CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
echo    EXIT;
echo.
pause

echo Step 3: Running migrations...
python manage.py migrate

if errorlevel 1 (
    echo Error: Migration failed. Please check your database configuration in .env
    exit /b 1
)

echo [OK] Migrations completed successfully
echo.

echo Step 4: Create superuser account
python manage.py createsuperuser

echo.
echo ===================================
echo Setup Complete!
echo ===================================
echo.
echo To start the development server:
echo   python manage.py runserver
echo.
echo Then visit:
echo   API: http://localhost:8000/
echo   Admin: http://localhost:8000/admin/
echo.
echo Next steps:
echo   - Import Sheerpluck data (Phase 3.3)
echo   - Create REST API endpoints (Phase 3.4)
echo   - Set up API documentation (Phase 3.4)
echo.
pause
