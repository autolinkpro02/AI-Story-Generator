"""Assemble scene images and narration into a simple vertical story video."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont
import textwrap


def _try_windows_tts(text: str, output_path: Path) -> bool:
    try:
        ps_script = (
            "$speech = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$speech.SetOutputToWaveFile('{path}'); "
            "$speech.SelectVoice('Microsoft Zira Desktop'); "
            "$speech.Speak('{speech}'); "
            "$speech.Dispose()"
        ).format(path=str(output_path).replace("'", "''"), speech=text.replace("'", "''"))
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True, capture_output=True, text=True)
        return output_path.exists()
    except Exception as exc:
        print(f"Windows TTS failed: {exc}")
        return False


def _load_bold_font(font_size: int):
    candidates = [
        "arialbd.ttf",
        "arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, font_size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=font_size)
    except Exception:
        return ImageFont.load_default()


def build_video(project: Any, script_data: dict[str, Any], progress_callback: Optional[callable] = None) -> list[Path]:
    """Create a basic vertical video from scene images and narration text."""
    project.output_dir.mkdir(parents=True, exist_ok=True)
    project.subtitles_dir.mkdir(parents=True, exist_ok=True)

    output_path = project.output_dir / f"{project.slug}.mp4"
    subtitle_path = project.subtitles_dir / "captions.srt"
    audio_path = project.audio_dir / "narration.mp3"

    scenes = script_data.get("scenes", [])
    if not scenes:
        return []

    # If per-scene audio exists, prefer actual audio durations for subtitle timing.
    lines = []
    total_duration = 0.0
    scene_audio_durations: dict[int, float] = {}
    # helper: get duration via ffprobe
    def _audio_duration(p: Path) -> float:
        try:
            import json

            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(p),
            ]
            out = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(out.stdout.strip())
        except Exception:
            return 0.0

    for scene in scenes:
        scene_number = scene.get("scene_number", 1)
        narration = scene.get("narration", "")
        # prefer actual audio file duration when available
        audio_file = project.audio_dir / f"scene_{scene_number:02d}.mp3"
        if audio_file.exists():
            duration = _audio_duration(audio_file)
            scene_audio_durations[scene_number] = duration
        else:
            duration = float(int(scene.get("duration_seconds", 3)))

        start = total_duration
        end = total_duration + duration
        total_duration = end
        lines.append(f"{scene_number}\n{_format_timestamp(int(start))} --> {_format_timestamp(int(end))}\n{narration}\n")

    subtitle_path.write_text("\n".join(lines), encoding="utf-8")

    # Also produce a WebVTT version for browser subtitle support
    try:
        vtt_path = project.subtitles_dir / "captions.vtt"
        with subtitle_path.open("r", encoding="utf-8") as fh_in, vtt_path.open("w", encoding="utf-8") as fh_out:
            fh_out.write("WEBVTT\n\n")
            for line in fh_in:
                # convert SRT timestamp commas to periods
                if "-->" in line:
                    fh_out.write(line.replace(",", "."))
                else:
                    fh_out.write(line)
        # prefer VTT for web delivery
        subtitle_path = vtt_path
    except Exception as exc:
        print(f"Failed to write VTT subtitles: {exc}")

    text_file = project.audio_dir / "narration.txt"
    narration_text = " ".join(scene.get("narration", "") for scene in scenes)
    text_file.write_text(narration_text, encoding="utf-8")

    # Prefer per-scene MP3s produced by `generate_narration_audio` when available.
    scene_mp3s = sorted(project.audio_dir.glob("scene_*.mp3"))
    if scene_mp3s:
        # Create a concat file for ffmpeg demuxer
        concat_file = project.audio_dir / "concat.txt"
        with concat_file.open("w", encoding="utf-8") as fh:
            for p in scene_mp3s:
                fh.write(f"file '{p.as_posix()}'\n")

        ffmpeg_concat_cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(audio_path),
        ]
        try:
            subprocess.run(ffmpeg_concat_cmd, check=True, capture_output=True, text=True)
        except Exception:
            # fallback: re-encode all files into a single mp3
            ffmpeg_reencode = ["ffmpeg", "-y"]
            for p in scene_mp3s:
                ffmpeg_reencode += ["-i", str(p)]
            ffmpeg_reencode += ["-filter_complex", f"concat=n={len(scene_mp3s)}:v=0:a=1 [a]", "-map", "[a]", str(audio_path)]
            subprocess.run(ffmpeg_reencode, check=True)
    else:
        # Fall back to Windows TTS or a sine tone when no per-scene audio exists
        if not _try_windows_tts(narration_text, project.audio_dir / "narration.wav"):
            duration_seconds = max(2, total_duration)
            ffmpeg_audio_cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=1000:duration={duration_seconds}",
                "-vn",
                "-acodec",
                "libmp3lame",
                str(audio_path),
            ]
            subprocess.run(ffmpeg_audio_cmd, check=True, capture_output=True, text=True)
        else:
            ffmpeg_audio_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(project.audio_dir / "narration.wav"),
                "-vn",
                "-acodec",
                "libmp3lame",
                str(audio_path),
            ]
            subprocess.run(ffmpeg_audio_cmd, check=True, capture_output=True, text=True)

    # Check for scene images
    missing_scenes = []
    for scene in scenes:
        scene_num = scene.get('scene_number', 1)
        scene_file = project.scenes_dir / f"scene_{scene_num:02d}.png"
        if not scene_file.exists():
            missing_scenes.append(scene_num)
    
    if missing_scenes:
        print(f"ERROR: Missing scene images for scenes: {missing_scenes}")
        print(f"Scene directory: {project.scenes_dir}")
        print(f"Directory exists: {project.scenes_dir.exists()}")
        if project.scenes_dir.exists():
            print(f"Files in directory: {list(project.scenes_dir.glob('scene_*.png'))}")
        return []
    
    # Ensure output directory exists
    project.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Calculate total duration and target frame count
    FPS = 24
    total_target_duration = sum(
        max(scene_audio_durations.get(s.get("scene_number", idx + 1), 0.0), float(s.get("duration_seconds", 5)))
        for idx, s in enumerate(scenes)
    )
    if total_target_duration <= 0:
        total_target_duration = 30.0

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", "1080x1920",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "pipe:0",
        "-i", str(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-profile:v", "baseline",
        "-level", "3.0",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-ac", "2",
        "-af", "volume=2.0,apad",
        "-t", f"{total_target_duration:.2f}",
        "-movflags", "+faststart",
        str(output_path),
    ]

    print("Launching FFmpeg process for direct in-memory frame piping...")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    total_scene_count = len(scenes)
    current_frame = 0
    motion_types = ["zoom_in", "pan_right", "zoom_out", "pan_left", "pan_up", "pulse_zoom"]

    for idx, scene in enumerate(scenes):
        scene_number = scene.get("scene_number", idx + 1)
        image_path = project.scenes_dir / f"scene_{scene_number:02d}.png"
        if not image_path.exists():
            continue

        # Respect requested scene target duration (e.g. 10s per scene for 60s / 1 Min videos)
        target_scene_dur = float(scene.get("duration_seconds", 5))
        audio_dur = scene_audio_durations.get(scene_number, 0.0)
        duration = max(audio_dur, target_scene_dur) if target_scene_dur > 0 else max(2.5, audio_dur)
        
        scene_frames = max(1, int(round(duration * FPS)))
        motion_type = motion_types[idx % len(motion_types)]

        with Image.open(image_path) as src_img:
            src_img = src_img.convert("RGBA")
            img_ratio = src_img.width / src_img.height
            target_ratio = 1080 / 1920
            if img_ratio > target_ratio:
                base_h = 2275
                base_w = int(2275 * img_ratio)
            else:
                base_w = 1280
                base_h = int(1280 / img_ratio)
            
            src_scaled = src_img.resize((base_w, base_h), Image.Resampling.BILINEAR)
            orig_w, orig_h = src_scaled.size

            # Pre-render scene gradient overlay and text drop-shadow ONCE per scene
            scene_overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(scene_overlay)
            for y in range(1250, 1920):
                alpha = int(230 * ((y - 1250) / 670))
                overlay_draw.line([(0, y), (1080, y)], fill=(0, 0, 0, alpha))

            # Big, Bold 68px High-Impact Subtitles for Shorts/Reels/TikTok
            font_size = 68
            font = _load_bold_font(font_size)

            caption_text = scene.get("narration", "")
            wrapped_lines = textwrap.wrap(caption_text, width=22)
            wrapped_text = "\n".join(wrapped_lines)
            
            bbox = overlay_draw.multiline_textbbox((0, 0), wrapped_text, font=font, spacing=10)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            tx = (1080 - text_w) // 2
            ty = 1600 - (text_h // 2)

            # Heavy black drop-shadow + Bold white/yellow subtitle text
            overlay_draw.multiline_text((tx + 3, ty + 3), wrapped_text, fill=(0, 0, 0, 255), font=font, align="center", spacing=10)
            overlay_draw.multiline_text((tx - 3, ty - 3), wrapped_text, fill=(0, 0, 0, 255), font=font, align="center", spacing=10)
            overlay_draw.multiline_text((tx, ty), wrapped_text, fill=(255, 255, 255, 255), font=font, align="center", spacing=10)

            for frame_num in range(scene_frames):
                current_frame += 1
                if progress_callback and frame_num % 15 == 0:
                    scene_pct = (idx / total_scene_count) + (frame_num / scene_frames / total_scene_count)
                    pct = 70 + int(25 * scene_pct)
                    progress_callback(f"Direct RAM pipe 24 FPS animation for Scene {idx+1}/{total_scene_count}...", pct)

                progress = frame_num / max(1, scene_frames - 1)

                target_w, target_h = 1080, 1920
                if motion_type == "zoom_in":
                    scale = 1.0 + 0.14 * progress
                    crop_w = int(target_w / scale)
                    crop_h = int(target_h / scale)
                    cx, cy = orig_w // 2, orig_h // 2
                elif motion_type == "zoom_out":
                    scale = 1.14 - 0.14 * progress
                    crop_w = int(target_w / scale)
                    crop_h = int(target_h / scale)
                    cx, cy = orig_w // 2, orig_h // 2
                elif motion_type == "pan_right":
                    scale = 1.10
                    crop_w = int(target_w / scale)
                    crop_h = int(target_h / scale)
                    max_shift = orig_w - crop_w
                    cx = (crop_w // 2) + int(max_shift * progress)
                    cy = orig_h // 2
                elif motion_type == "pan_left":
                    scale = 1.10
                    crop_w = int(target_w / scale)
                    crop_h = int(target_h / scale)
                    max_shift = orig_w - crop_w
                    cx = (orig_w - crop_w // 2) - int(max_shift * progress)
                    cy = orig_h // 2
                elif motion_type == "pan_up":
                    scale = 1.10
                    crop_w = int(target_w / scale)
                    crop_h = int(target_h / scale)
                    max_shift = orig_h - crop_h
                    cx = orig_w // 2
                    cy = (orig_h - crop_h // 2) - int(max_shift * progress)
                else:  # pulse_zoom
                    scale = 1.0 + 0.08 * (1.0 - abs(progress - 0.5) * 2)
                left = max(0, min(orig_w - crop_w, cx - crop_w // 2))
                top = max(0, min(orig_h - crop_h, cy - crop_h // 2))
                right = left + crop_w
                bottom = top + crop_h

                cropped = src_scaled.crop((left, top, right, bottom))
                canvas = cropped.resize((1080, 1920), Image.Resampling.BILINEAR)
                canvas = Image.alpha_composite(canvas, scene_overlay).convert("RGB")

                # Stream raw frame bytes directly into FFmpeg stdin pipe (0 disk files!)
                try:
                    proc.stdin.write(canvas.tobytes())
                except Exception as exc:
                    print(f"FFmpeg pipe write error: {exc}")
                    break

    if progress_callback:
        progress_callback("Finalizing MP4 video container...", 96)

    if proc.stdin:
        proc.stdin.flush()
        proc.stdin.close()
    proc.wait()

    return [output_path, subtitle_path, audio_path]


def _format_timestamp(seconds: float) -> str:
    # Format seconds as SRT timestamp with milliseconds: HH:MM:SS,mmm
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"
