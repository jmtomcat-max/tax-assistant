$ErrorActionPreference = 'Stop'

$ffmpeg = Join-Path $PSScriptRoot '..\.venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe'
$inputVideo = Join-Path $PSScriptRoot 'media\TAX_ASSISTANT_V7_ENDING_BOOST.mp4'
$filter = Join-Path $PSScriptRoot 'precision_sample_filter.txt'
$outputVideo = Join-Path $PSScriptRoot 'media\REVIEW_SAMPLE_13S_23S_INTERNAL_EXPERIENCE_R2.mp4'

if (Test-Path -LiteralPath $outputVideo) { throw "Output already exists: $outputVideo" }

& $ffmpeg -hide_banner -i $inputVideo -filter_complex_script $filter -map '[v]' -map '[a]' -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -c:a aac -b:a 196k -movflags +faststart $outputVideo
if ($LASTEXITCODE -ne 0) { throw "FFmpeg failed with exit code $LASTEXITCODE" }

Get-Item -LiteralPath $outputVideo | Select-Object FullName, Length, LastWriteTime
