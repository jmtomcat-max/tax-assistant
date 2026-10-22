@echo off
chcp 65001 > nul
title GitHub 푸시 (tax-assistant)
cd /d "%~dp0"

echo ======================================================================
echo   CJ프레시웨이 세무 판례 AI 비서 - GitHub 저장소로 코드 푸시
echo ======================================================================
echo   대상 저장소: https://github.com/jmtomcat-max/tax-assistant.git
echo   브랜치: main
echo ======================================================================
echo.

git push -u origin main

if errorlevel 1 (
    echo.
    echo [오류] 푸시 중 문제가 발생했습니다. GitHub 로그인 상태를 확인해 주세요.
) else (
    echo.
    echo [성공] GitHub에 코드가 성공적으로 업로드되었습니다!
    echo 이제 share.streamlit.io 에서 앱을 배포할 수 있습니다.
)

echo.
pause
