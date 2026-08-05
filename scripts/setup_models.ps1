param(
    [switch]$PullOllama = $true
)

Write-Host "Model setup helper"
if ($PullOllama) {
    $ollama = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollama) {
        Write-Warning "'ollama' not found on PATH. Install Ollama from https://ollama.com and try again."
    } else {
        Write-Host "Reading model name from config.py..."
        $model = & .venv\Scripts\python.exe - <<'PY'
import sys
sys.path.append('.')
from config import OLLAMA_MODEL
print(OLLAMA_MODEL)
PY
        if ($LASTEXITCODE -ne 0 -or -not $model) {
            Write-Warning "Couldn't determine OLLAMA_MODEL from config.py. Edit config.py to set OLLAMA_MODEL."
        } else {
            Write-Host "Pulling Ollama model: $model"
            ollama pull $model
        }
    }
}

Write-Host "Piper TTS setup: See Piper documentation for building voices. This script does not automate Piper builds." 
