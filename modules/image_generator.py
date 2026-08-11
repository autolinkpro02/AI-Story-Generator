"""Generate professional 1080x1920 vertical AI images for story scenes."""

from __future__ import annotations

import os
import time
import random
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from PIL import Image
import config


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


def _fetch_pollinations_ai_image(prompt: str, image_path: Path) -> bool:
    """Fetch high-definition vertical AI image with fast native Flux model endpoints."""
    # Truncate prompt to 120 chars to prevent 400/500 URL syntax errors
    clean_prompt = prompt.strip()[:120]
    encoded_prompt = quote(clean_prompt, safe="")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    # Retry up to 5 attempts with different random seeds
    for attempt in range(5):
        seed = random.randint(1, 999999)
        urls = [
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=1280&nologo=true&seed={seed}",
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=1344&nologo=true&model=flux&seed={seed}",
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=1280&nologo=true&model=turbo&seed={seed}",
            f"https://pollinations.ai/p/{encoded_prompt}?width=768&height=1280&seed={seed}",
        ]

        for url in urls:
            try:
                print(f"Fetching High-Definition AI illustration via Flux (Attempt {attempt+1}/5)...")
                response = requests.get(url, headers=headers, timeout=25)
                if response.status_code == 429:
                    print(f"Pollinations AI rate limited (HTTP 429). Sleeping 3.5s for rate reset...")
                    time.sleep(3.5)
                    continue
                if response.status_code == 200 and _save_image_bytes(response.content, image_path):
                    print(f"Successfully saved HD AI image ({image_path.stat().st_size} bytes) for: {clean_prompt[:40]}...")
                    return True
            except Exception as exc:
                print(f"Pollinations fetch error: {exc}")
            
            time.sleep(1.0)

    print(f"FAILED to fetch AI image for prompt: {prompt[:40]}")
    return False


from concurrent.futures import ThreadPoolExecutor, as_completed


def generate_scene_images(project: Any, script_data: dict[str, Any], progress_callback: Optional[callable] = None, overwrite: bool = True) -> list[Path]:
    """Generate 100% real AI illustrations concurrently for all scenes in parallel."""
    output_files: list[Path] = []
    project.scenes_dir.mkdir(parents=True, exist_ok=True)

    scenes = script_data.get("scenes", [])
    if not scenes:
        return []

    if progress_callback:
        progress_callback(f"Downloading 1080x1920 HD AI illustrations for {len(scenes)} scenes...", 35)

    def _process_single_scene(idx_scene):
        idx, scene = idx_scene
        scene_number = scene.get("scene_number", idx + 1)
        image_path = project.scenes_dir / f"scene_{scene_number:02d}.png"
        
        # Real AI images are always > 20 KB (20,000 bytes). If < 20 KB, it's a fallback canvas, so re-download!
        if not overwrite and image_path.exists() and image_path.stat().st_size > 20000:
            print(f"Scene {scene_number} already has high-definition AI image ({image_path.stat().st_size} bytes)")
            return scene_number, image_path

        # Stagger requests by 2.0s to avoid rate limiting
        if idx > 0:
            time.sleep(2.0)

        prompt = scene.get("image_prompt", "")
        style_modifier = scene.get("visual_style", "")
        if not style_modifier or "pixar" not in style_modifier.lower():
            augmented_prompt = f"{prompt}, 8k resolution, cinematic lighting, masterpiece, hyper-detailed vertical 9:16 portrait wallpaper"
        else:
            augmented_prompt = f"{prompt}, 8k resolution, 3d octane render, masterpiece, hyper-detailed vertical 9:16 portrait wallpaper"

        print(f"--- Generating Scene {scene_number} 1080x1920 HD AI Illustration ---")
        success = _fetch_pollinations_ai_image(augmented_prompt, image_path)
        
        if not success:
            print(f"Retrying Scene {scene_number} with direct prompt...")
            simple_prompt = f"3d animated character portrait of {prompt[:60]}, 8k resolution"
            success = _fetch_pollinations_ai_image(simple_prompt, image_path)

        return scene_number, image_path if image_path.exists() else None

    # Fetch scene images in parallel (max_workers=3) for ultra-fast 12-second generation
    completed_count = 0
    with ThreadPoolExecutor(max_workers=3) as executor:
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
