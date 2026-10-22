$ErrorActionPreference = 'Stop'

$ffmpeg = Join-Path $PSScriptRoot '..\.venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe'
$inputVideo = Join-Path $PSScriptRoot '..\flow_takeout_20261007\Takeout\Flow\media\a422c229-8f84-400f-90a1-1d694871d0b9.mp4'
$filter = Join-Path $PSScriptRoot 'clip01_filter_r3.txt'
$outputVideo = Join-Path $PSScriptRoot 'media\REVIEW_CLIP01_INTERNAL_EXPERIENCE_R3.mp4'

if (-not (Test-Path -LiteralPath $inputVideo)) { throw "Input clip not found: $inputVideo" }
if (Test-Path -LiteralPath $outputVideo) { throw "Output already exists: $outputVideo" }

& $ffmpeg -hide_banner -i $inputVideo -filter_complex_script $filter -map '[v]' -map '0:a?' -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -c:a copy -movflags +faststart $outputVideo
if ($LASTEXITCODE -ne 0) { throw "FFmpeg failed with exit code $LASTEXITCODE" }

Get-Item -LiteralPath $outputVideo | Select-Object FullName, Length, LastWriteTime
