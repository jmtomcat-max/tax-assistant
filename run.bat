@echo off
chcp 65001 > nul
title CJ프레시웨이 세무 판례 AI 비서 실행
cd /d "%~dp0"

echo ======================================================================
echo   CJ프레시웨이 세무 판례 AI 비서 - 실행 모드를 선택해 주세요
echo ======================================================================
echo   [1] 로컬 안전 실행 (기본 권장: 사내 전용 localhost, 외부 노출 차단)
echo       -> run_local.bat 실행
echo.
echo   [2] 외부 공유 실행 (주의: Cloudflare Tunnel 외부 공개, 사내 보안정책 확인)
echo       -> run_share.bat 실행
echo ======================================================================
echo.

choice /c 12 /t 5 /d 1 /m "실행 모드를 선택하세요 (기본 1번 5초 후 자동 실행): "
if errorlevel 2 goto SHARE
if errorlevel 1 goto LOCAL

:LOCAL
call run_local.bat
goto END

:SHARE
call run_share.bat
goto END

:END
