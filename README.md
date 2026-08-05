# Story Automation -- build log

Tuned for: Intel i5-6300U (dual-core, no dedicated GPU), 12GB RAM, Windows.
Hardware mode: **Low-Spec** (see `config.py`).

## Status: Milestone 1 -- script generation ✅

What's here so far:
- `config.py` -- all model/path settings in one place
- `modules/project_manager.py` -- creates the `projects/story-name/` folder
  layout and tracks which pipeline stage has finished, so a crash resumes
  instead of starting over
- `modules/script_generator.py` -- calls a local Ollama model, gets back
  structured JSON (title, hook, character description, 6-10 scenes with
  narration + image prompts, closing line), validates it, and retries with
  the specific problems fed back to the model if the shape is off

Not built yet: image generation (FastSD CPU), narration (Piper TTS),
captions, FFmpeg assembly, the Gradio UI, and packaging (start.bat, full
README, troubleshooting guide).

## Try it now

1. Install [Ollama](https://ollama.com) (Windows installer).
2. Open a terminal and run:
   ```
   ollama serve
   ```
   Leave that running. In a second terminal:
   ```
   ollama pull llama3.2:3b
   ```
   (~2GB download, one time.)
3. From this project folder:
   ```
   pip install -r requirements.txt
   python test_script_generator.py
   ```

On this hardware, expect the generation itself to take anywhere from
~30 seconds to a couple of minutes -- that's normal for CPU-only inference
on a dual-core chip. If `llama3.2:3b` gives unreliable JSON after a few
tries, edit `OLLAMA_MODEL` in `config.py` to `"phi3:mini"` and
`ollama pull phi3:mini` instead -- it's a similar size but tuned harder for
structured output.

Output lands in `projects/<story-title-slug>/script.json` and `script.txt`.

## Next up

Image generation via **FastSD CPU** (not Fooocus/ComfyUI -- full SDXL on
this CPU would take minutes per image). FastSD CPU is purpose-built for
CPU-only machines and ships a REST API we can call per scene, same pattern
as the Ollama module above.

## TTS Backends

- **Default (available):** `gTTS` is used when installed (see `modules/narration_generator.py`). Install with `pip install gTTS`.
- **Optional (recommended):** `edge-tts` (Microsoft Edge neural voices) can be installed with `pip install edge-tts` for higher-quality offline-like voices; the code will use it if present.
- **Windows fallback:** a PowerShell-based `System.Speech` method is attempted by `modules/video_builder.py` when other backends are missing (requires Windows desktop APIs).
- **Notes:** `ffmpeg` must be installed and on `PATH` to assemble audio+frames into MP4 (used by `generate_video.py` / `modules/video_builder.py`).

If you want to force a specific backend, install the desired package in the project's virtualenv and re-run the generation commands above.

## Setup & Start (Windows)

1. Run the installer script (creates virtualenv and installs Python deps):

```powershell
.\install_windows.ps1
```

2. Pull the Ollama model (in another terminal run the Ollama service first):

```powershell
ollama serve
ollama pull llama3.2:3b
```

You can also run the helper:

```powershell
.\scripts\setup_models.ps1
```

3. Start the local web UI (double-click `start.bat` or run):

```powershell
.\start.bat
```

The app listens on `http://127.0.0.1:8000` by default.

## Notes on status

- FFmpeg assembly and the local web UI are working; `generate_video.py` builds a 9:16 MP4 from the `projects/` sample assets.  
- Ollama-based script generation is implemented but requires `ollama serve` and the model to be pulled.  
- Piper TTS setup is still manual; see Piper documentation for building voices.

### Regenerating a single scene from the UI

1. Open `http://127.0.0.1:8000` in your browser.
2. Use the "Regenerate single scene" form near the bottom of the page to specify a `projects/<story-slug>` path and a scene number, then click `Regenerate scene`.
3. The UI will queue the job, poll status, and show links to the regenerated assets and reassembled MP4 when finished.

### Piper helper

Run the helper to check `piper` availability and get build hints:

```powershell
.\scripts\setup_piper.ps1
```

### Installer FFmpeg download (optional)

When running `.\install_windows.ps1`, if `ffmpeg` is not found it can optionally download a static build for you into `./tools/ffmpeg.zip`; you still need to unzip it and add the `bin` folder to your `PATH`.


