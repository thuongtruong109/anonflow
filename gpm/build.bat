@echo off
echo ================================================
echo Anonflow - Build GUI Application
echo ================================================
echo.

cd /d "%~dp0"

echo [1/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo.

echo [2/3] Building executable with PyInstaller...
pyinstaller --clean build.spec
if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)
echo.

robocopy "data" "dist\anonflow\data" /E /IS /IT
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
    echo ERROR: Failed to copy data files (robocopy exit code %RC%)
    pause
    exit /b %RC%
)
echo Data copied successfully (robocopy exit code %RC%)
echo [3/3] Build completed successfully!
echo.
echo ================================================
echo Executable location:
echo %CD%\dist\anonflow\app.exe
echo ================================================
echo.
echo You can now run the application!
echo.

pause
