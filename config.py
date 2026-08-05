import os
from pathlib import Path

HARDWARE_MODE = os.getenv("HARDWARE_MODE", "low_spec")  # "gpu" | "low_spec"

# --- Script generation (Ollama) ---
OLLAMA_URL = os.getenv("OLLAMA_URL", "https://ollama-railway-production-b452.up.railway.app/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")       # ~2GB, runs acceptably on a weak CPU
OLLAMA_MODEL_BACKUP = "phi3:mini"  # try this if llama3.2:3b's JSON is unreliable
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "600"))       # generation timeout

# --- Image generation (FastSD CPU) ---
IMAGE_BACKEND = "fastsdcpu"
FASTSDCPU_API_URL = "http://localhost:8000/api/generate"  # confirmed when we build this module
IMAGE_WIDTH = 512
IMAGE_HEIGHT = 512   # square, matches how the small turbo/LCM models were trained;
                     # FFmpeg crops/pads this to the 1080x1920 vertical canvas later

# When True, always use the local placeholder image generator instead of
# calling external services (Pollinations / Hugging Face). Useful for fast
# consistent testing when you don't need photoreal images.
FORCE_PLACEHOLDERS = False

# Image style preferences: set to 'cinematic' to bias prompts toward cinematic
# photographic qualities. Set to 'default' for no extra style modifiers.
IMAGE_STYLE = "cinematic"  # options: 'cinematic' | 'default'

# When True, encourage original / unique compositions (avoid stock-like results)
IMAGE_ORIGINALITY = True

# --- Voice (Piper TTS) ---
PIPER_VOICE = "en_US-lessac-medium"  # confirmed when we build the voice module

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent
PROJECTS_DIR = PROJECT_ROOT / "projects"
ASSETS_DIR = PROJECT_ROOT / "assets"
MUSIC_DIR = ASSETS_DIR / "music"

# --- Video output ---
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
OUTPUT_FPS = 30
