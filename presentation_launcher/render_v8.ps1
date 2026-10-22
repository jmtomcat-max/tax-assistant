$ErrorActionPreference = 'Stop'

$ffmpeg = Join-Path $PSScriptRoot '..\.venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe'
$inputVideo = Join-Path $PSScriptRoot 'media\TAX_ASSISTANT_V7_ENDING_BOOST.mp4'
$filter = Join-Path $PSScriptRoot 'v8_filter.txt'
$outputVideo = Join-Path $PSScriptRoot 'media\TAX_ASSISTANT_V8_TEXT_FIXED_R2.mp4'

if (-not (Test-Path -LiteralPath $ffmpeg)) { throw "FFmpeg not found: $ffmpeg" }
if (-not (Test-Path -LiteralPath $inputVideo)) { throw "Input video not found: $inputVideo" }
if (Test-Path -LiteralPath $outputVideo) { throw "Output already exists: $outputVideo" }

& $ffmpeg -hide_banner -y -i $inputVideo -filter_complex_script $filter -map '[v]' -map '0:a?' -c:v libx264 -preset medium -crf 17 -pix_fmt yuv420p -c:a copy -movflags +faststart $outputVideo
if ($LASTEXITCODE -ne 0) { throw "FFmpeg failed with exit code $LASTEXITCODE" }

Get-Item -LiteralPath $outputVideo | Select-Object FullName, Length, LastWriteTime
