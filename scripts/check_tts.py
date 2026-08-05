import importlib, shutil, sys, subprocess

results = {}
for mod in ('gtts','edge_tts'):
    try:
        __import__(mod)
        results[mod] = True
    except Exception:
        results[mod] = False

# Check FFmpeg and PowerShell availability
results['ffmpeg_in_path'] = shutil.which('ffmpeg') is not None
results['powershell_in_path'] = shutil.which('powershell') is not None

# Try to import win32com or check System.Speech availability via PowerShell dry-run
powershell_tts = False
if results['powershell_in_path']:
    try:
        ps = """
        try {
            $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
            $s.Dispose()
            Write-Output 'ok'
        } catch {
            Write-Output 'no'
        }
        """
        proc = subprocess.run(['powershell','-NoProfile','-Command',ps], capture_output=True, text=True)
        powershell_tts = 'ok' in proc.stdout.lower()
    except Exception:
        powershell_tts = False
results['windows_system_speech'] = powershell_tts

print('RESULTS:')
for k,v in results.items():
    print(f"{k}: {v}")

# Exit code 0
sys.exit(0)
