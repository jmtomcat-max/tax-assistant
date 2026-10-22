# CJ프레시웨이 세무 판례 AI 비서 - 외부 공유 모드 (PowerShell)
$Host.UI.RawUI.WindowTitle = "CJ프레시웨이 세무 판례 AI 비서 [외부 공유 모드 - 보안 주의]"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "######################################################################" -ForegroundColor Red
Write-Host "#                                                                    #" -ForegroundColor Red
Write-Host "#               [보안 경고] 외부 인터넷 공유 모드 실행               #" -ForegroundColor Yellow
Write-Host "#                                                                    #" -ForegroundColor Red
Write-Host "######################################################################" -ForegroundColor Red
Write-Host "  1. Cloudflare Tunnel을 통해 임시 공개 웹 URL이 생성됩니다." -ForegroundColor Yellow
Write-Host "  2. URL 링크를 보유한 외부 사용자 누구나 시스템에 접근할 수 있습니다." -ForegroundColor Yellow
Write-Host "  3. 사내 기밀, 고객 개인정보, 비공개 세무 문서를 입력하지 마십시오." -ForegroundColor Red
Write-Host "  4. 테스트 종료 후 반드시 이 창을 닫아 터널을 즉시 중단하십시오." -ForegroundColor Red
Write-Host "######################################################################" -ForegroundColor Red
Write-Host ""

$env:IS_TUNNEL_MODE = "true"

Write-Host "[1/2] Streamlit 서버를 백그라운드에서 시작합니다..." -ForegroundColor Cyan
Start-Process -FilePath ".venv\Scripts\streamlit.exe" -ArgumentList "run app.py --server.headless=true --server.port=8501" -NoNewWindow

Write-Host "[2/2] Cloudflare 보안 터널을 연결합니다..." -ForegroundColor Cyan
Write-Host "(잠시 후 생성되는 https://....trycloudflare.com 링크를 확인해 주세요)" -ForegroundColor Green
Write-Host ""

& .\cloudflared.exe tunnel --url http://localhost:8501
