# CJ프레시웨이 세무 판례 AI 비서 - 외부 공유 모드 (PowerShell)
$Host.UI.RawUI.WindowTitle = "CJ프레시웨이 세무 판례 AI 비서 [외부 공유 모드 - 보안 주의]"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "######################################################################" -ForegroundColor Red
Write-Host "#                                                                    #" -ForegroundColor Red
Write-Host "#               [보안 경고] 외부 인터넷 공유 모드 실행               #" -ForegroundColor Yellow
Write-Host "#                                                                    #" -ForegroundColor Red
Write-Host "######################################################################" -ForegroundColor Red
Write-Host "  1. Cloudflare Tunnel 링크는 인터넷 외부에서 누구나 접속 가능한 공개 URL입니다." -ForegroundColor Red
Write-Host "  2. 회사 내부자료, 개인정보, 실제 세무검토 사례 입력 전 사내 보안정책을 반드시 확인하십시오." -ForegroundColor Red
Write-Host "  3. 사내 기밀 데이터나 미공개 회계자료를 절대 테스트용으로 입력하지 마십시오." -ForegroundColor Yellow
Write-Host "  4. 외부 공유 테스트가 끝난 후에는 반드시 이 콘솔 창을 닫아 터널을 즉시 종료하십시오." -ForegroundColor Yellow
Write-Host "######################################################################" -ForegroundColor Red
Write-Host ""

$env:IS_TUNNEL_MODE = "true"

Write-Host "[1/2] Streamlit 서버를 백그라운드에서 시작합니다..." -ForegroundColor Cyan
Start-Process -FilePath ".venv\Scripts\streamlit.exe" -ArgumentList "run app.py --server.headless=true --server.port=8501" -NoNewWindow

Write-Host "[2/2] Cloudflare 보안 터널을 연결합니다..." -ForegroundColor Cyan
Write-Host "(잠시 후 생성되는 https://....trycloudflare.com 링크를 확인해 주세요)" -ForegroundColor Green
Write-Host ""

& .\cloudflared.exe tunnel --url http://localhost:8501
