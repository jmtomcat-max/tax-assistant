$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

function New-RoundedPath([System.Drawing.RectangleF]$rect, [float]$radius) {
    $path = [System.Drawing.Drawing2D.GraphicsPath]::new()
    $diameter = $radius * 2
    $arc = [System.Drawing.RectangleF]::new($rect.X, $rect.Y, $diameter, $diameter)
    $path.AddArc($arc, 180, 90)
    $arc.X = $rect.Right - $diameter; $path.AddArc($arc, 270, 90)
    $arc.Y = $rect.Bottom - $diameter; $path.AddArc($arc, 0, 90)
    $arc.X = $rect.X; $path.AddArc($arc, 90, 90)
    $path.CloseFigure()
    return $path
}

$output = Join-Path $PSScriptRoot 'media\status_pill_analysis.png'
$bitmap = [System.Drawing.Bitmap]::new(1280, 720, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.Clear([System.Drawing.Color]::Transparent)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

foreach ($layer in @(
    @{ X = 429; Y = 639; W = 422; H = 57; A = 18 },
    @{ X = 431; Y = 637; W = 418; H = 57; A = 28 },
    @{ X = 433; Y = 636; W = 414; H = 56; A = 38 }
)) {
    $rect = [System.Drawing.RectangleF]::new($layer.X, $layer.Y, $layer.W, $layer.H)
    $path = New-RoundedPath $rect 28
    $brush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb($layer.A, 20, 31, 29))
    $graphics.FillPath($brush, $path)
    $brush.Dispose(); $path.Dispose()
}

$pillRect = [System.Drawing.RectangleF]::new(433, 632, 414, 55)
$pillPath = New-RoundedPath $pillRect 27.5
$gradient = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
    $pillRect,
    [System.Drawing.Color]::FromArgb(255, 62, 82, 78),
    [System.Drawing.Color]::FromArgb(255, 43, 59, 56),
    [System.Drawing.Drawing2D.LinearGradientMode]::Vertical
)
$graphics.FillPath($gradient, $pillPath)

$text = '분석 근거를 확인하고 있습니다. 잠시만 기다려주세요.'
$font = [System.Drawing.Font]::new('Malgun Gothic', 15, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$textBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(242, 255, 255, 255))
$format = [System.Drawing.StringFormat]::new()
$format.Alignment = [System.Drawing.StringAlignment]::Center
$format.LineAlignment = [System.Drawing.StringAlignment]::Center
$graphics.DrawString($text, $font, $textBrush, $pillRect, $format)

$bitmap.Save($output, [System.Drawing.Imaging.ImageFormat]::Png)
$format.Dispose(); $textBrush.Dispose(); $font.Dispose(); $gradient.Dispose(); $pillPath.Dispose(); $graphics.Dispose(); $bitmap.Dispose()
Get-Item -LiteralPath $output | Select-Object FullName, Length
