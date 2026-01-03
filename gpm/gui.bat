@echo off
echo ================================================
echo GPM Automation - Build GUI Application
echo ================================================
echo.

cd /d "%~dp0"

echo [1/3] Installing dependencies...
pip install -r requirements-gui.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo.

echo [2/3] Building executable with PyInstaller...
pyinstaller --clean gui_app.spec
if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)
echo.

echo [3/3] Build completed successfully!
echo.
echo ================================================
echo Executable location:
echo %CD%\dist\GPM_Automation\GPM_Automation.exe
echo ================================================
echo.
echo You can now run the application!
echo.

pause
