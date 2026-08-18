"""Generate professional 1080x1920 vertical AI images for story scenes using real FLUX.1."""

from __future__ import annotations

import os
import time
import random
from io import BytesIO
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from PIL import Image, ImageDraw, ImageOps, ImageFilter, ImageEnhance
import config

print(f"[image_generator] LOADED FROM: {__file__}  (HF FLUX.1-schnell + Pollinations fallback build)")

HF_MODEL = os.environ.get("HUGGINGFACE_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
print(f"[image_generator] HF_MODEL={HF_MODEL}")


def _save_image_bytes(image_bytes: bytes, image_path: Path) -> bool:
    try:
        # Real AI images are > 20 KB (20,000 bytes). Reject low-res fallback canvases (< 20 KB)
        if not image_bytes or len(image_bytes) < 20000:
            print(f"Rejected low-res image ({len(image_bytes) if image_bytes else 0} bytes < 20,000 bytes)")
            return False
        image_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            image.save(image_path, format="PNG")
        return True
    except Exception as exc:
        print(f"Failed to save image bytes to {image_path}: {exc}")
        return False


def _enhance_image(image_path: Path) -> None:
    """Fit to exact 1080x1920 and apply ONE light sharpen/color pass.
    This is the only place enhancement happens - video_builder no longer
    re-sharpens on top of this, which was stacking two aggressive unsharp
    masks and producing haloed, gritty-looking edges."""
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        img = ImageOps.fit(img, (1080, 1920), Image.Resampling.LANCZOS)
        img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=80, threshold=2))
        img = ImageEnhance.Sharpness(img).enhance(1.15)
        img = ImageEnhance.Color(img).enhance(1.03)
        img.save(image_path, "PNG")


def _fetch_hf_flux_image(prompt: str, image_path: Path) -> bool:
    """Fetch a real FLUX.1-schnell image from Hugging Face's hosted Inference API.
    Requires an HF_TOKEN env var (free account, free-tier inference).
    Returns False (never raises) so the caller can fall through to Pollinations."""
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_TOKEN")
    if not hf_token:
        return False

    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {
        "inputs": prompt.strip()[:400],
        "parameters": {"width": 768, "height": 1344},  # near 9:16, kept modest for free-tier compute limits
    }

    for attempt in range(3):
        try:
            print(f"Fetching FLUX.1-schnell from Hugging Face (attempt {attempt + 1}/3)...")
            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=60)

            if response.status_code == 503:
                # Model is cold-starting on HF's side - it tells us how long to wait
                try:
                    wait_for = float(response.json().get("estimated_time", 20))
                except Exception:
                    wait_for = 20
                print(f"HF model is loading, waiting {wait_for:.0f}s...")
                time.sleep(min(wait_for, 40))
                continue

            if response.status_code == 429:
                print("Hugging Face rate limited. Waiting 10s...")
                time.sleep(10)
                continue

            if response.status_code == 200 and response.headers.get("content-type", "").startswith("image"):
                if _save_image_bytes(response.content, image_path):
                    _enhance_image(image_path)
                    print(f"Saved FLUX.1 image ({image_path.stat().st_size} bytes) via Hugging Face")
                    return True

            print(f"HF response not usable: status={response.status_code} content-type={response.headers.get('content-type')}")
        except Exception as exc:
            print(f"Hugging Face fetch error: {exc}")

        time.sleep(2.0)

    return False


def _fetch_pollinations_ai_image(prompt: str, image_path: Path) -> bool:
    """Fallback path: Pollinations' free/anonymous 'flux' alias. Used only if HF_TOKEN
    isn't set or Hugging Face fails - this endpoint has been unreliable in testing."""
    clean_prompt = prompt.strip()[:200]
    encoded_prompt = quote(clean_prompt, safe="")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    wait_seconds = 5.0
    for attempt in range(3):
        seed = random.randint(1, 999999)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true&model=flux&seed={seed}"

        try:
            print(f"Fetching Pollinations flux image (attempt {attempt + 1}/3)...")
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 429:
                print(f"Pollinations rate limited (HTTP 429). Backing off {wait_seconds:.0f}s...")
                time.sleep(wait_seconds)
                wait_seconds = min(wait_seconds * 2, 40.0)
                continue
            if response.status_code == 200 and _save_image_bytes(response.content, image_path):
                _enhance_image(image_path)
                print(f"Saved Pollinations image ({image_path.stat().st_size} bytes) for: {clean_prompt[:40]}...")
                return True
        except Exception as exc:
            print(f"Pollinations fetch error: {exc}")

        time.sleep(1.5)

    print(f"FAILED to fetch AI image for prompt: {prompt[:40]}")
    return False


def generate_scene_images(project: Any, script_data: dict[str, Any], progress_callback: Optional[callable] = None, overwrite: bool = True) -> list[Path]:
    """Generate one FLUX.1 illustration per scene, matching each scene's own image_prompt."""
    output_files: list[Path] = []
    project.scenes_dir.mkdir(parents=True, exist_ok=True)

    scenes = script_data.get("scenes", [])
    if not scenes:
        return []

    if not (os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_TOKEN")):
        print("NOTE: HF_TOKEN not set - skipping real FLUX.1 and using Pollinations fallback for every scene.")

    if progress_callback:
        progress_callback(f"Generating {len(scenes)} scene illustrations with FLUX.1...", 35)

    def _process_single_scene(idx_scene):
        idx, scene = idx_scene
        scene_number = scene.get("scene_number", idx + 1)
        image_path = project.scenes_dir / f"scene_{scene_number:02d}.png"

        if not overwrite and image_path.exists() and image_path.stat().st_size > 20000:
            print(f"Scene {scene_number} already has an image ({image_path.stat().st_size} bytes) - skipping")
            return scene_number, image_path

        # Small random stagger so concurrent requests don't all hit an API in the same instant
        time.sleep(random.uniform(0.2, 1.2))

        prompt = scene.get("image_prompt", "")
        style = scene.get("visual_style", "")
        full_prompt = f"{prompt}, {style}".strip(", ") if style else prompt

        print(f"--- Generating Scene {scene_number}: {full_prompt[:60]}... ---")
        success = _fetch_hf_flux_image(full_prompt, image_path)
        if not success:
            success = _fetch_pollinations_ai_image(full_prompt, image_path)

        if not success:
            # Last-resort fallback so the pipeline doesn't stop dead - a labeled placeholder frame
            img = Image.new("RGB", (1080, 1920), (15, 23, 42))
            draw = ImageDraw.Draw(img)
            draw.text((100, 900), f"Scene {scene_number}\n{prompt[:40]}...", fill=(226, 232, 240))
            img.save(image_path, "PNG")
            print(f"WARNING: Scene {scene_number} fell back to a placeholder frame - all image sources failed")

        return scene_number, image_path

    # Fetch scenes one at a time - keeps behavior predictable across whichever
    # backend (HF or Pollinations) ends up serving a given scene.
    completed_count = 0
    with ThreadPoolExecutor(max_workers=1) as executor:
        future_map = {executor.submit(_process_single_scene, (i, s)): i for i, s in enumerate(scenes)}
        for future in as_completed(future_map):
            completed_count += 1
            scene_num, img_p = future.result()
            if img_p and img_p.exists():
                output_files.append(img_p)
            if progress_callback:
                pct = 30 + int(30 * completed_count / len(scenes))
                progress_callback(f"Generated AI illustration for {completed_count}/{len(scenes)} scenes...", pct)

    # Sort by scene number to maintain order
    output_files.sort(key=lambda p: p.name)
    return output_files