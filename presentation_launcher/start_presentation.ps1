param([switch]$CheckOnly)

$launcherDir = $PSScriptRoot
$videoPath = Join-Path $launcherDir 'media\TAX_ASSISTANT_NEW_NARRATED_SUNHI.mp4'
$vlcCandidates = @(
    "$env:ProgramFiles\VideoLAN\VLC\vlc.exe",
    "${env:ProgramFiles(x86)}\VideoLAN\VLC\vlc.exe"
)
$vlcPath = $vlcCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (-not (Test-Path -LiteralPath $videoPath)) { throw "발표 영상을 찾을 수 없습니다: $videoPath" }
if (-not $vlcPath) { throw 'VLC를 찾을 수 없습니다. VideoLAN 공식 VLC를 설치해 주세요.' }
if ((Get-Item -LiteralPath $videoPath).Length -lt 1MB) { throw '발표 영상 파일이 비정상적으로 작습니다.' }

if ($CheckOnly) {
    Write-Host "[OK] 발표 런처 준비 완료"
    Write-Host "[OK] 영상: $videoPath"
    Write-Host "[OK] 플레이어: $vlcPath"
    exit 0
}

Start-Process -FilePath $vlcPath -ArgumentList @(
    '--fullscreen',
    '--play-and-exit',
    '--no-video-title-show',
    '--no-one-instance',
    '--no-qt-error-dialogs',
    "`"$videoPath`""
)
