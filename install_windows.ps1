<#
Install and prepare the project on Windows.
Runs in an elevated PowerShell session if needed.
#>
Write-Host "Setting up virtual environment and Python dependencies..."
if (-Not (Test-Path -Path .\.venv)) {
    python -m venv .venv
}
Write-Host "Activating virtual environment..."
. .venv\Scripts\Activate.ps1
Write-Host "Installing Python requirements..."
pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Checking ffmpeg on PATH..."
if (-Not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Warning "ffmpeg not found on PATH."
    $choice = Read-Host "Download a static FFmpeg build to ./tools/ffmpeg.zip now? (y/N)"
    if ($choice -and $choice.ToLower().StartsWith('y')) {
        $outDir = Join-Path (Get-Location) 'tools'
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
        $zipPath = Join-Path $outDir 'ffmpeg.zip'
        Write-Host "Downloading a static FFmpeg build (may take a while)..."
        $url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
        Invoke-WebRequest -Uri $url -OutFile $zipPath
        Write-Host "Downloaded to $zipPath. Please unzip and add the ffmpeg bin folder to your PATH."
    } else {
        Write-Warning "Please install FFmpeg and add it to PATH. See https://ffmpeg.org/download.html"
    }
} else {
    Write-Host "ffmpeg found."
}

Write-Host "Setup complete. Next steps:"
Write-Host "  1) Install Ollama from https://ollama.com and run `ollama serve` in a separate terminal."
Write-Host "  2) Pull the recommended model (example): `ollama pull llama3.2:3b`"
Write-Host "  3) (Optional) Set up Piper TTS following the project's README or Piper documentation."
Write-Host "  4) Start the app: double-click start.bat or run `python web_app.py` inside the activated virtualenv."
