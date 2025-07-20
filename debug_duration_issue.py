#!/usr/bin/env python3
"""
Debug script to specifically test the audio duration issue.
"""

import subprocess
import shutil
from pathlib import Path

def test_duration_commands():
    """Test different ways to get audio duration."""
    print("🔍 Testing Audio Duration Commands")
    print("=" * 40)
    
    audio_file = "/home/ragha/code/paper_agent_2/slides/audio/slide01.wav"
    
    # Test ffprobe
    ffprobe_path = shutil.which("ffprobe")
    ffmpeg_path = shutil.which("ffmpeg")
    
    print(f"ffprobe path: {ffprobe_path}")
    print(f"ffmpeg path: {ffmpeg_path}")
    
    if ffprobe_path:
        print("\n=== Testing ffprobe ===")
        cmd = [ffprobe_path, "-i", audio_file, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"]
        print(f"Command: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            print(f"Return code: {result.returncode}")
            print(f"stdout: '{result.stdout.strip()}'")
            print(f"stderr: '{result.stderr.strip()}'")
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                print(f"✅ Duration: {duration} seconds")
            else:
                print("❌ ffprobe failed")
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    # Test the fallback logic from the original code
    print("\n=== Testing Original Logic ===")
    ffprobe_path_fallback = shutil.which("ffprobe") or ffmpeg_path
    print(f"Using path: {ffprobe_path_fallback}")
    
    cmd = [ffprobe_path_fallback, "-i", audio_file, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"]
    print(f"Command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(f"Return code: {result.returncode}")
        print(f"stdout: '{result.stdout.strip()}'")
        print(f"stderr: '{result.stderr.strip()}'")
        if result.returncode == 0:
            duration = float(result.stdout.strip())
            print(f"✅ Duration: {duration} seconds")
        else:
            print("❌ Command failed")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test alternative method using ffmpeg
    print("\n=== Testing ffmpeg alternative ===")
    cmd = [ffmpeg_path, "-i", audio_file, "-f", "null", "-", "-v", "quiet", "-stats"]
    print(f"Command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(f"Return code: {result.returncode}")
        print(f"stdout: '{result.stdout.strip()}'")
        print(f"stderr: '{result.stderr.strip()}'")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_duration_commands()
