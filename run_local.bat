@echo off
chcp 65001 > nul
title CJ프레시웨이 세무 판례 AI 비서 [로컬 안전 모드]
cd /d "%~dp0"

echo ======================================================================
echo   CJ프레시웨이 세무 판례 AI 비서 - 로컬 안전 모드
echo ======================================================================
echo   * 접속 주소: http://localhost:8501 (또는 http://127.0.0.1:8501)
echo   * 세무 판례 AI 비서를 시작하고 있습니다... (약 10~15초 소요)
echo   * 잠시 기다리시면 웹 브라우저가 자동으로 열립니다.
echo.
echo   [★ 중요 안내]
echo   이 검은색 콘솔 창이 켜져 있는 동안에만 프로그램이 작동합니다.
echo   창을 닫지 마시고, 최소화(-)하여 내려두세요!
echo   (이 창을 닫으면 프로그램이 즉시 종료됩니다)
echo ======================================================================
echo.

set IS_TUNNEL_MODE=false
if "%HTTP_PROXY%"=="http://127.0.0.1:9" set HTTP_PROXY=
if "%HTTPS_PROXY%"=="http://127.0.0.1:9" set HTTPS_PROXY=
if "%ALL_PROXY%"=="http://127.0.0.1:9" set ALL_PROXY=

if not exist "%~dp0.venv\Scripts\streamlit.exe" goto NO_VENV

rem 7초 후 자동으로 기본 브라우저를 띄우는 보조 헬퍼
start "" cmd /c "timeout /t 7 > nul & start http://localhost:8501"

"%~dp0.venv\Scripts\streamlit.exe" run app.py --server.headless=false --server.port=8501

if errorlevel 1 goto ON_ERROR
goto END

:NO_VENV
echo.
echo [오류] 가상환경 .venv 폴더 또는 streamlit.exe를 찾을 수 없습니다.
pause
exit /b 1

:ON_ERROR
echo.
echo ======================================================================
echo [알림] 실행 중 오류가 발생했거나 이미 프로그램이 실행 중입니다.
echo - 이미 켜져 있다면 브라우저에서 http://localhost:8501 로 접속해 보세요.
echo ======================================================================
pause
exit /b 1

:END
