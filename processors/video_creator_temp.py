"""Temporary copy of video_creator with flexible create_video signature.
Adds optional `output_path` parameter to accept call from streamlit_app_enhanced.py
while retaining backward-compatibility with older 2- or 3-arg calls.
"""
import os
import subprocess
import shutil
import tempfile
import time
from pathlib import Path


def create_video(frames_dir, audio_dir, output_path=None, progress_callback=None):
    """Create video from slide PNGs and audio tracks.

    Parameters
    ----------
    frames_dir : str
        Directory containing `deck.###.png` still images.
    audio_dir : str
        Directory containing `*.wav` narration clips.
    output_path : str | Path | None, optional
        Desired output `.mp4` path.  If ``None`` a default `slides/video.mp4` is used.
    progress_callback : callable(msg:str, current:int|None, total:int|None) | None
        Callback for UI progress updates.  Falls back to `print` when ``None``.

    Returns
    -------
    str | None
        Absolute path to the generated video, or ``None`` if creation failed.
    """
    def update_progress(msg, current=None, total=None):
        if progress_callback:
            progress_callback(msg, current, total)
        else:
            print(msg)

    # Resolve output location early so the path can be reported consistently
    if output_path is None:
        slides_dir = Path("slides")
        slides_dir.mkdir(parents=True, exist_ok=True)
        output_path = slides_dir / "video.mp4"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        update_progress("Error: ffmpeg not found. Please install ffmpeg.")
        return None

    temp_dir = Path(tempfile.mkdtemp(prefix="video_temp_"))
    try:
        # Slight delay ensures filesystem settles (important on some OS/filesystems)
        time.sleep(1)

        frames_dir = Path(frames_dir)
        audio_dir = Path(audio_dir)
        if not frames_dir.exists():
            update_progress(f"Frames directory does not exist: {frames_dir}")
            return None
        if not audio_dir.exists():
            update_progress(f"Audio directory does not exist: {audio_dir}")
            return None

        png_files = sorted(frames_dir.glob("deck.*.png"))
        audio_files = sorted(audio_dir.glob("*.wav"))
        if not png_files:
            update_progress("No PNG frames found – aborting video creation.")
            return None
        if not audio_files:
            update_progress("No audio tracks found – aborting video creation.")
            return None

        # 1) Standardise audio (16-bit PCM, 44.1 kHz, stereo)
        update_progress("Pre-processing audio…")
        std_audio = []
        for idx, wav in enumerate(audio_files):
            update_progress("Audio", idx, len(audio_files))
            out = temp_dir / f"std_{wav.name}"
            cmd = [ffmpeg_path, "-y", "-i", str(wav), "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", str(out)]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            std_audio.append(out)

        # 2) Create per-slide clips combining still + narration
        update_progress("Creating clips…")
        clips = []
        for idx, audio in enumerate(std_audio):
            if idx >= len(png_files):
                update_progress(f"No image for slide {idx+1}; skipping clip.")
                continue
            img = png_files[idx]
            clip_out = temp_dir / f"clip_{idx+1:02d}.mp4"
            # Determine narration duration via ffprobe (falls back to ffmpeg)
            probe = shutil.which("ffprobe") or ffmpeg_path
            dur = float(subprocess.check_output([probe, "-i", str(audio), "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"]).decode().strip())
            cmd = [ffmpeg_path, "-y", "-loop", "1", "-i", str(img), "-i", str(audio), "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-shortest", "-t", str(dur), str(clip_out)]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            clips.append(clip_out)

        if not clips:
            update_progress("No clips generated; aborting video creation.")
            return None

        # 3) Concatenate clips
        update_progress("Concatenating clips…")
        concat_file = temp_dir / "concat.txt"
        with open(concat_file, "w") as f:
            for c in clips:
                f.write(f"file '{c}'\n")
        cmd = [ffmpeg_path, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output_path)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        update_progress(f"✅ Video created: {output_path}")
        return str(output_path)
    except Exception as e:
        update_progress(f"Error creating video: {e}")
        return None
    finally:
        shutil.rmtree(temp_dir)
