# CJ프레시웨이 세무 판례 AI 비서 - 로컬 안전 모드 (PowerShell)
$Host.UI.RawUI.WindowTitle = "CJ프레시웨이 세무 판례 AI 비서 [로컬 안전 모드]"
Set-Location $PSScriptRoot

Write-Host "======================================================================" -ForegroundColor Green
Write-Host "  CJ프레시웨이 세무 판례 AI 비서 - 로컬 안전 모드" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "  * 접속 주소: http://localhost:8501" -ForegroundColor Cyan
Write-Host "  * 보안 상태: 외부 인터넷에 노출되지 않는 사내 전용 로컬 실행입니다." -ForegroundColor Gray
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""

$env:IS_TUNNEL_MODE = "false"
# Codex/일부 개발 도구가 주입하는 연결 불가 프록시가 외부 API 호출을 막지 않게 합니다.
if ($env:HTTP_PROXY -eq "http://127.0.0.1:9") { Remove-Item Env:HTTP_PROXY }
if ($env:HTTPS_PROXY -eq "http://127.0.0.1:9") { Remove-Item Env:HTTPS_PROXY }
if ($env:ALL_PROXY -eq "http://127.0.0.1:9") { Remove-Item Env:ALL_PROXY }
& .venv\Scripts\streamlit.exe run app.py --server.headless=false --server.port=8501
