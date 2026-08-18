"""Assemble scene images and narration into a vertical story video."""

from __future__ import annotations

import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance


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
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
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


def _audio_duration(p: Path) -> float:
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(p),
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(out.stdout.strip())
    except Exception:
        return 0.0


def _format_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _render_scene_frame(image_path: Path, narration: str) -> Image.Image:
    """Composite one scene image with its caption pill, ONCE, as a single still frame.
    FFmpeg (not Python) handles repeating this frame for the scene's duration."""
    with Image.open(image_path) as src_img:
        src_img = src_img.convert("RGB")
        img_ratio = src_img.width / src_img.height
        target_ratio = 1080 / 1920

        if img_ratio > target_ratio:
            new_h = 1920
            new_w = int(1920 * img_ratio)
        else:
            new_w = 1080
            new_h = int(1080 / img_ratio)

        resized = src_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - 1080) // 2
        top = (new_h - 1920) // 2
        cropped = resized.crop((left, top, left + 1080, top + 1920))

        # NOTE: no sharpening here - image_generator._enhance_image already applied
        # one pass when the image was fetched. Applying it again here (as an earlier
        # version did) stacked two unsharp masks and produced haloed/gritty edges.

        frame = Image.new("RGBA", (1080, 1920), (0, 0, 0, 255))
        frame.paste(cropped, (0, 0))

        overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        font = _load_bold_font(40)

        wrapped_lines = textwrap.wrap(narration, width=42)
        wrapped_text = "\n".join(wrapped_lines)

        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, spacing=8)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        tx = (1080 - text_w) // 2
        ty = 1640 - (text_h // 2)

        pad_x, pad_y = 24, 14
        box_rect = [tx - pad_x, ty - pad_y, tx + text_w + pad_x, ty + text_h + pad_y]
        draw.rounded_rectangle(box_rect, radius=16, fill=(10, 15, 26, 175), outline=(255, 255, 255, 35), width=1)
        draw.multiline_text((tx + 1, ty + 1), wrapped_text, fill=(0, 0, 0, 220), font=font, align="center", spacing=8)
        draw.multiline_text((tx, ty), wrapped_text, fill=(255, 255, 255, 255), font=font, align="center", spacing=8)

        return Image.alpha_composite(frame, overlay).convert("RGB")


def build_video(project: Any, script_data: dict[str, Any], progress_callback: Optional[callable] = None) -> list[Path]:
    """Create the vertical video from scene images and narration."""
    project.output_dir.mkdir(parents=True, exist_ok=True)
    project.subtitles_dir.mkdir(parents=True, exist_ok=True)

    output_path = project.output_dir / f"{project.slug}.mp4"
    subtitle_path = project.subtitles_dir / "captions.srt"
    audio_path = project.audio_dir / "narration.mp3"

    scenes = script_data.get("scenes", [])
    if not scenes:
        return []

    # --- Subtitles: use real per-scene audio duration where available ---
    lines = []
    total_duration = 0.0
    for scene in scenes:
        scene_number = scene.get("scene_number", 1)
        narration = scene.get("narration", "")
        audio_file = project.audio_dir / f"scene_{scene_number:02d}.mp3"
        duration = _audio_duration(audio_file) if audio_file.exists() else 0.0
        if duration <= 0:
            duration = float(scene.get("duration_seconds", 3)) or 3.0

        start = total_duration
        end = total_duration + duration
        total_duration = end
        lines.append(f"{scene_number}\n{_format_timestamp(start)} --> {_format_timestamp(end)}\n{narration}\n")

    subtitle_path.write_text("\n".join(lines), encoding="utf-8")

    try:
        vtt_path = project.subtitles_dir / "captions.vtt"
        with subtitle_path.open("r", encoding="utf-8") as fh_in, vtt_path.open("w", encoding="utf-8") as fh_out:
            fh_out.write("WEBVTT\n\n")
            for line in fh_in:
                fh_out.write(line.replace(",", ".") if "-->" in line else line)
        subtitle_path = vtt_path
    except Exception as exc:
        print(f"Failed to write VTT subtitles: {exc}")

    # --- Narration audio: concat per-scene mp3s, padded to match each scene's on-screen duration ---
    scene_mp3s = sorted(project.audio_dir.glob("scene_*.mp3"))
    if scene_mp3s:
        padded_mp3s = []
        for idx, scene in enumerate(scenes):
            scene_number = scene.get("scene_number", idx + 1)
            raw_audio = project.audio_dir / f"scene_{scene_number:02d}.mp3"
            if not raw_audio.exists():
                continue

            spoken_dur = _audio_duration(raw_audio)
            req_dur = float(scene.get("duration_seconds", 10.0) or 10.0)
            target_dur = max(req_dur, spoken_dur + 0.3)
            scene["duration_seconds"] = target_dur

            padded_audio = project.audio_dir / f"scene_{scene_number:02d}_sync.mp3"
            if spoken_dur <= 0:
                # raw_audio is corrupt/unreadable (0 duration) - generate silence
                # of the target length instead of feeding a broken file into ffmpeg
                # concat later, which previously crashed the entire video build.
                print(f"WARNING: scene {scene_number} audio unreadable - substituting {target_dur:.1f}s of silence")
                silence_cmd = [
                    "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
                    "-t", f"{target_dur:.2f}", "-c:a", "libmp3lame", "-b:a", "192k",
                    str(padded_audio),
                ]
                try:
                    subprocess.run(silence_cmd, check=True, capture_output=True, text=True)
                    padded_mp3s.append(padded_audio)
                except Exception as exc:
                    print(f"Silence fallback also failed for scene {scene_number}: {exc}")
                continue

            pad_cmd = [
                "ffmpeg", "-y", "-i", str(raw_audio),
                "-af", f"apad=whole_dur={target_dur:.2f}",
                "-c:a", "libmp3lame", "-b:a", "192k",
                str(padded_audio),
            ]
            try:
                subprocess.run(pad_cmd, check=True, capture_output=True, text=True)
                padded_mp3s.append(padded_audio)
            except Exception as exc:
                print(f"Audio padding warning for scene {scene_number}: {exc}")
                padded_mp3s.append(raw_audio)

        concat_file = project.audio_dir / "concat.txt"
        with concat_file.open("w", encoding="utf-8") as fh:
            for p in (padded_mp3s if padded_mp3s else scene_mp3s):
                fh.write(f"file '{p.as_posix()}'\n")

        ffmpeg_concat_cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(audio_path)]
        try:
            subprocess.run(ffmpeg_concat_cmd, check=True, capture_output=True, text=True)
        except Exception:
            ffmpeg_reencode = ["ffmpeg", "-y"]
            for p in (padded_mp3s if padded_mp3s else scene_mp3s):
                ffmpeg_reencode += ["-i", str(p)]
            n = len(padded_mp3s if padded_mp3s else scene_mp3s)
            ffmpeg_reencode += ["-filter_complex", f"concat=n={n}:v=0:a=1 [a]", "-map", "[a]", str(audio_path)]
            subprocess.run(ffmpeg_reencode, check=True)
    else:
        narration_text = " ".join(s.get("narration", "") for s in scenes)
        if not _try_windows_tts(narration_text, project.audio_dir / "narration.wav"):
            duration_seconds = max(2, total_duration)
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency=1000:duration={duration_seconds}",
                 "-vn", "-acodec", "libmp3lame", str(audio_path)],
                check=True, capture_output=True, text=True,
            )
        else:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(project.audio_dir / "narration.wav"),
                 "-vn", "-acodec", "libmp3lame", str(audio_path)],
                check=True, capture_output=True, text=True,
            )

    # --- Check scene images exist ---
    missing_scenes = [
        s.get("scene_number", 1) for s in scenes
        if not (project.scenes_dir / f"scene_{s.get('scene_number', 1):02d}.png").exists()
    ]
    if missing_scenes:
        print(f"ERROR: Missing scene images for scenes: {missing_scenes}")
        return []

    # --- Build video ---
    # FAST PATH: pre-render one composited PNG frame per scene, then hand FFmpeg the
    # images directly (-loop 1 -t duration per input + concat filter). FFmpeg repeats
    # each still frame internally at C speed, instead of Python writing every raw
    # frame (potentially 1000+ frames, several GB) through a stdin pipe.
    FPS = 24
    total_target_duration = float(script_data.get("duration_seconds", 60) or 60)
    if total_target_duration <= 0:
        total_target_duration = 60.0

    with tempfile.TemporaryDirectory(dir=project.output_dir) as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        cmd = ["ffmpeg", "-y"]
        filter_parts = []
        input_index = 0

        for idx, scene in enumerate(scenes):
            scene_number = scene.get("scene_number", idx + 1)
            image_path = project.scenes_dir / f"scene_{scene_number:02d}.png"
            duration = float(scene.get("duration_seconds", 10))
            if duration <= 0:
                duration = 10.0

            if progress_callback:
                pct = 70 + int(20 * (idx / len(scenes)))
                progress_callback(f"Compositing Scene {idx + 1}/{len(scenes)}...", pct)

            frame_img = _render_scene_frame(image_path, scene.get("narration", ""))
            frame_path = tmp_dir / f"frame_{scene_number:02d}.png"
            frame_img.save(frame_path, "PNG")

            cmd += ["-loop", "1", "-t", f"{duration:.2f}", "-i", str(frame_path)]
            filter_parts.append(f"[{input_index}:v]fps={FPS},format=yuv420p,setsar=1[v{input_index}]")
            input_index += 1

        audio_input_index = input_index
        cmd += ["-i", str(audio_path)]

        concat_inputs = "".join(f"[v{i}]" for i in range(input_index))
        filter_complex = ";".join(filter_parts) + f";{concat_inputs}concat=n={input_index}:v=1:a=0[outv]"

        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", f"{audio_input_index}:a",
            "-c:v", "libx264",
            "-preset", "fast",       # was "slow" - main speed win #1
            "-tune", "stillimage",
            "-crf", "19",            # was 10 (near-lossless/huge) - visually excellent, much faster - win #2
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-ac", "2",
            "-af", "volume=2.0,apad",
            "-t", f"{total_target_duration:.2f}",
            "-movflags", "+faststart",
            str(output_path),
        ]

        if progress_callback:
            progress_callback("Encoding final MP4 with FFmpeg...", 92)

        print("Running FFmpeg (native image-loop + concat, no raw-frame piping)...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg error:\n{result.stderr[-3000:]}")
            raise RuntimeError("FFmpeg encoding failed - see log above")

    if progress_callback:
        progress_callback("Video generation completed!", 100)

    return [output_path, subtitle_path, audio_path]