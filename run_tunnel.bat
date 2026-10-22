@echo off
chcp 65001 > nul
title CJ프레시웨이 세무 판례 AI 비서 [외부 인터넷 공유 모드 - 보안 주의]
cd /d "%~dp0"

echo.
echo ######################################################################
echo #                                                                    #
echo #               [보안 경고] 외부 인터넷 공유 모드 실행               #
echo #                                                                    #
echo ######################################################################
echo   1. Cloudflare Tunnel 링크는 인터넷 외부에서 누구나 접속 가능한 공개 URL입니다.
echo   2. 회사 내부자료, 개인정보, 실제 세무검토 사례 입력 전 사내 보안정책을 반드시 확인하십시오.
echo   3. 사내 기밀 데이터나 미공개 회계자료를 절대 테스트용으로 입력하지 마십시오.
echo   4. 외부 공유 테스트가 끝난 후에는 반드시 이 콘솔 창을 닫아 터널을 즉시 종료하십시오.
echo ######################################################################
echo.

set IS_TUNNEL_MODE=true
if "%HTTP_PROXY%"=="http://127.0.0.1:9" set HTTP_PROXY=
if "%HTTPS_PROXY%"=="http://127.0.0.1:9" set HTTPS_PROXY=
if "%ALL_PROXY%"=="http://127.0.0.1:9" set ALL_PROXY=

echo [1/2] Streamlit 서버를 백그라운드에서 시작합니다...
start /b "" "%~dp0.venv\Scripts\streamlit.exe" run app.py --server.headless=true --server.port=8501

echo [2/2] Cloudflare 보안 터널을 연결합니다...
echo (잠시 후 생성되는 https://....trycloudflare.com 링크를 복사하여 공유할 수 있습니다)
echo.
"%~dp0cloudflared.exe" tunnel --url http://localhost:8501
pause
