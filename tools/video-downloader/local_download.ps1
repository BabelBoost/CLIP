$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ToolsDir = Join-Path $Root '.local-tools'
$DownloadsDir = Join-Path $env:USERPROFILE 'Downloads'

New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null
New-Item -ItemType Directory -Force -Path $DownloadsDir | Out-Null

$YtDlp = Join-Path $ToolsDir 'yt-dlp.exe'
$Deno = Join-Path $ToolsDir 'deno.exe'
$FfmpegMarker = Join-Path $ToolsDir 'ffmpeg-ready.txt'

function Download-File {
    param(
        [Parameter(Mandatory=$true)][string]$Url,
        [Parameter(Mandatory=$true)][string]$Destination
    )
    Write-Host "Pobieram: $Url"
    Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
}

function Ensure-YtDlp {
    if (-not (Test-Path $YtDlp)) {
        Write-Host 'Instaluję lokalnie yt-dlp...'
        Download-File 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe' $YtDlp
    }
    else {
        Write-Host 'Sprawdzam aktualizację yt-dlp...'
        try { & $YtDlp -U | Out-Host } catch { Write-Host 'Nie udało się zaktualizować yt-dlp. Używam obecnej wersji.' }
    }
}

function Ensure-Deno {
    if (Test-Path $Deno) { return }

    Write-Host 'Instaluję lokalnie silnik JavaScript Deno...'
    $Zip = Join-Path $ToolsDir 'deno.zip'
    Download-File 'https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip' $Zip
    Expand-Archive -Path $Zip -DestinationPath $ToolsDir -Force
    Remove-Item $Zip -Force -ErrorAction SilentlyContinue
}

function Ensure-FFmpeg {
    $Existing = Get-ChildItem -Path $ToolsDir -Filter 'ffmpeg.exe' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($Existing) { return $Existing.FullName }

    Write-Host 'Instaluję lokalnie FFmpeg...'
    $Zip = Join-Path $ToolsDir 'ffmpeg.zip'
    $Extract = Join-Path $ToolsDir 'ffmpeg'
    Download-File 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' $Zip
    New-Item -ItemType Directory -Force -Path $Extract | Out-Null
    Expand-Archive -Path $Zip -DestinationPath $Extract -Force
    Remove-Item $Zip -Force -ErrorAction SilentlyContinue

    $Found = Get-ChildItem -Path $Extract -Filter 'ffmpeg.exe' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $Found) { throw 'Nie znaleziono ffmpeg.exe po rozpakowaniu.' }
    return $Found.FullName
}

function Invoke-VideoDownload {
    param(
        [Parameter(Mandatory=$true)][string]$Url,
        [string]$Browser = ''
    )

    $Ffmpeg = Ensure-FFmpeg
    $FfmpegDir = Split-Path -Parent $Ffmpeg
    $Template = Join-Path $DownloadsDir '%(title).180B [%(id)s].%(ext)s'

    $Args = @(
        '--no-playlist',
        '--windows-filenames',
        '--merge-output-format', 'mp4',
        '--remux-video', 'mp4',
        '--ffmpeg-location', $FfmpegDir,
        '--js-runtimes', "deno:$Deno",
        '--remote-components', 'ejs:github',
        '-f', 'bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b[ext=mp4]/b',
        '-o', $Template
    )

    if ($Browser) {
        $Args += @('--cookies-from-browser', $Browser)
    }

    $Args += $Url

    & $YtDlp @Args
    return $LASTEXITCODE
}

Clear-Host
Write-Host '=========================================='
Write-Host ' Babel Boost Video Downloader - LOCAL'
Write-Host '=========================================='
Write-Host ''
Write-Host "Pliki będą zapisywane tutaj: $DownloadsDir"
Write-Host ''

try {
    Ensure-YtDlp
    Ensure-Deno
    $null = Ensure-FFmpeg
}
catch {
    Write-Host ''
    Write-Host 'Nie udało się przygotować narzędzi.' -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ''
    Read-Host 'Naciśnij Enter, aby zamknąć'
    exit 1
}

Write-Host ''
$Url = Read-Host 'Wklej link do filmu YouTube, X lub Facebook'
if ([string]::IsNullOrWhiteSpace($Url)) {
    Write-Host 'Nie podano linku.'
    Read-Host 'Naciśnij Enter, aby zamknąć'
    exit 0
}

Write-Host ''
Write-Host 'Pobieram film na tym komputerze...'
$Code = Invoke-VideoDownload -Url $Url

if ($Code -ne 0) {
    Write-Host ''
    Write-Host 'Pierwsza próba nie powiodła się.' -ForegroundColor Yellow
    Write-Host 'Jeżeli film normalnie otwiera się w Twojej przeglądarce, można użyć jej cookies.'
    Write-Host 'Wpisz E dla Edge, C dla Chrome albo naciśnij Enter, aby zakończyć.'
    $Choice = (Read-Host 'Wybór').Trim().ToUpperInvariant()

    if ($Choice -eq 'E') {
        $Code = Invoke-VideoDownload -Url $Url -Browser 'edge'
    }
    elseif ($Choice -eq 'C') {
        $Code = Invoke-VideoDownload -Url $Url -Browser 'chrome'
    }
}

Write-Host ''
if ($Code -eq 0) {
    Write-Host 'GOTOWE.' -ForegroundColor Green
    Write-Host "Film został zapisany w: $DownloadsDir"
    Start-Process explorer.exe $DownloadsDir
}
else {
    Write-Host 'Pobieranie nie zakończyło się powodzeniem.' -ForegroundColor Red
    Write-Host 'Sprawdź, czy film odtwarza się w przeglądarce na tym komputerze.'
}

Write-Host ''
Read-Host 'Naciśnij Enter, aby zamknąć'
