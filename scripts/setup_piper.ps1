<#
Helper for Piper TTS setup on Windows.
This script checks for a `piper` executable and prints recommended commands to build voices.
It does not attempt a full build because Piper's build steps vary by platform and require Rust/tooling.
#>
Write-Host "Piper TTS helper"

$piper = Get-Command piper -ErrorAction SilentlyContinue
if ($piper) {
    Write-Host "Found piper at: $($piper.Path)"
    Write-Host "To list available voices: piper --list-voices"
    Write-Host "To synthesize a sample: piper --voice <voice> ""Hello world"" --output sample.wav"
    exit 0
}

Write-Host "piper executable not found on PATH. Common next steps:"
Write-Host "  1) Install Rust toolchain (https://rustup.rs)
  2) Clone the Piper repo (example: https://github.com/rhasspy/piper)
  3) Follow Piper's README to build the binary and voice models."
Write-Host "This script cannot safely automate voice model compilation across all Windows setups. See Piper docs for detailed steps."
