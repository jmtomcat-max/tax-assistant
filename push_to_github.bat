@echo off
cd /d "%~dp0"
echo ======================================================
echo   Pushing code to GitHub: jmtomcat-max/tax-assistant
echo ======================================================
echo.
git push -u origin main
echo.
if errorlevel 1 (
    echo [ERROR] Push failed.
) else (
    echo [SUCCESS] Code pushed to GitHub successfully!
)
echo.
pause
