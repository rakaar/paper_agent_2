#!/usr/bin/env python3
"""
Debug script to test video creation process step by step.
This will help identify where the bottleneck is in the video creation pipeline.
"""

import subprocess
import shutil
import tempfile
import time
from pathlib import Path
import os

def check_ffmpeg():
    """Check if ffmpeg is available and working."""
    print("=== Checking FFmpeg ===")
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        print("❌ Error: ffmpeg not found. Please install ffmpeg.")
        return None
    
    print(f"✅ FFmpeg found at: {ffmpeg_path}")
    
    # Test ffmpeg version
    try:
        result = subprocess.run([ffmpeg_path, "-version"], 
                              capture_output=True, text=True, timeout=10)
        print(f"✅ FFmpeg version: {result.stdout.split()[2]}")
        return ffmpeg_path
    except Exception as e:
        print(f"❌ Error testing ffmpeg: {e}")
        return None

def analyze_files():
    """Analyze the input files (frames and audio)."""
    print("\n=== Analyzing Input Files ===")
    
    frames_dir = Path("/home/ragha/code/paper_agent_2/slides/frames")
    audio_dir = Path("/home/ragha/code/paper_agent_2/slides/audio")
    
    # Check frames
    png_files = sorted(frames_dir.glob("deck.*.png"))
    print(f"📁 Found {len(png_files)} PNG files:")
    for png in png_files[:3]:  # Show first 3
        print(f"   - {png.name} ({png.stat().st_size} bytes)")
    if len(png_files) > 3:
        print(f"   ... and {len(png_files) - 3} more")
    
    # Check audio files
    audio_files = sorted(audio_dir.glob("*.wav"))
    print(f"🔊 Found {len(audio_files)} audio files:")
    for audio in audio_files[:3]:  # Show first 3
        print(f"   - {audio.name} ({audio.stat().st_size} bytes)")
    if len(audio_files) > 3:
        print(f"   ... and {len(audio_files) - 3} more")
    
    return png_files, audio_files

def test_single_clip_creation(ffmpeg_path, png_files, audio_files):
    """Test creating a single video clip."""
    print("\n=== Testing Single Clip Creation ===")
    
    if not png_files or not audio_files:
        print("❌ No files to test with")
        return False
    
    temp_dir = Path(tempfile.mkdtemp(prefix="debug_video_"))
    try:
        png_file = png_files[0]
        audio_file = audio_files[0]
        output_clip = temp_dir / "test_clip.mp4"
        
        print(f"🎬 Creating test clip with:")
        print(f"   Image: {png_file.name}")
        print(f"   Audio: {audio_file.name}")
        
        # Get audio duration (using the same logic as the main script)
        print("⏱️  Getting audio duration...")
        start_time = time.time()
        ffprobe_path = shutil.which("ffprobe") or ffmpeg_path  # Use ffprobe if available
        duration_cmd = [ffprobe_path, "-i", str(audio_file), "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"]
        print(f"   Using command: {' '.join(duration_cmd)}")
        try:
            duration_output = subprocess.check_output(duration_cmd, timeout=30).decode("utf-8").strip()
            duration = float(duration_output)
            print(f"✅ Audio duration: {duration:.2f} seconds (took {time.time() - start_time:.2f}s)")
        except subprocess.TimeoutExpired:
            print("❌ Timeout getting audio duration!")
            return False
        except Exception as e:
            print(f"❌ Error getting audio duration: {e}")
            return False
        
        # Create single clip
        print("🎥 Creating video clip...")
        start_time = time.time()
        clip_cmd = [
            ffmpeg_path, 
            "-loop", "1", 
            "-i", str(png_file),
            "-i", str(audio_file),
            "-c:v", "libx264", 
            "-tune", "stillimage",
            "-c:a", "aac", 
            "-b:a", "192k",
            "-pix_fmt", "yuv420p", 
            "-shortest", 
            "-t", str(duration),
            "-y",  # Overwrite output files
            str(output_clip)
        ]
        
        print(f"Command: {' '.join(clip_cmd)}")
        
        try:
            result = subprocess.run(clip_cmd, capture_output=True, text=True, timeout=120)
            elapsed = time.time() - start_time
            
            if result.returncode == 0:
                print(f"✅ Single clip created successfully in {elapsed:.2f}s")
                print(f"   Output size: {output_clip.stat().st_size} bytes")
                return True
            else:
                print(f"❌ FFmpeg failed (took {elapsed:.2f}s)")
                print(f"   stdout: {result.stdout}")
                print(f"   stderr: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Timeout creating single clip (>120s)!")
            return False
        except Exception as e:
            print(f"❌ Error creating single clip: {e}")
            return False
            
    finally:
        shutil.rmtree(temp_dir)

def test_audio_preprocessing(ffmpeg_path, audio_files):
    """Test audio preprocessing step."""
    print("\n=== Testing Audio Preprocessing ===")
    
    if not audio_files:
        print("❌ No audio files to test")
        return False
    
    temp_dir = Path(tempfile.mkdtemp(prefix="debug_audio_"))
    try:
        audio_file = audio_files[0]
        standardized_path = temp_dir / f"std_{audio_file.name}"
        
        print(f"🔧 Preprocessing audio: {audio_file.name}")
        start_time = time.time()
        
        standardize_cmd = [
            ffmpeg_path,
            "-i", str(audio_file),
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            "-y",  # Overwrite
            str(standardized_path)
        ]
        
        try:
            result = subprocess.run(standardize_cmd, capture_output=True, text=True, timeout=60)
            elapsed = time.time() - start_time
            
            if result.returncode == 0:
                print(f"✅ Audio preprocessing successful in {elapsed:.2f}s")
                print(f"   Output size: {standardized_path.stat().st_size} bytes")
                return True
            else:
                print(f"❌ Audio preprocessing failed (took {elapsed:.2f}s)")
                print(f"   stderr: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Timeout in audio preprocessing (>60s)!")
            return False
        except Exception as e:
            print(f"❌ Error in audio preprocessing: {e}")
            return False
            
    finally:
        shutil.rmtree(temp_dir)

def check_existing_video():
    """Check if there's already a video and its properties."""
    print("\n=== Checking Existing Video ===")
    
    video_path = Path("/home/ragha/code/paper_agent_2/slides/video.mp4")
    if video_path.exists():
        size = video_path.stat().st_size
        print(f"📹 Existing video found: {size} bytes ({size/1024/1024:.2f} MB)")
        
        # Try to get video info
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            try:
                info_cmd = [ffmpeg_path, "-i", str(video_path)]
                result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=10)
                # FFmpeg outputs info to stderr
                info = result.stderr
                
                # Extract duration if possible
                import re
                duration_match = re.search(r'Duration: (\d+:\d+:\d+\.\d+)', info)
                if duration_match:
                    print(f"   Duration: {duration_match.group(1)}")
                
                # Check if it mentions any errors
                if "Invalid data found" in info or "moov atom not found" in info:
                    print("⚠️  Video file may be corrupted or incomplete")
                else:
                    print("✅ Video file appears to be valid")
                    
            except Exception as e:
                print(f"⚠️  Could not get video info: {e}")
    else:
        print("📹 No existing video found")

def main():
    """Run all debug tests."""
    print("🔍 Video Creation Debug Script")
    print("=" * 50)
    
    # Check ffmpeg
    ffmpeg_path = check_ffmpeg()
    if not ffmpeg_path:
        return
    
    # Check existing video
    check_existing_video()
    
    # Analyze files
    png_files, audio_files = analyze_files()
    
    if not png_files or not audio_files:
        print("❌ Missing required files. Cannot proceed with tests.")
        return
    
    # Test audio preprocessing
    if not test_audio_preprocessing(ffmpeg_path, audio_files):
        print("❌ Audio preprocessing failed. This might be the bottleneck.")
        return
    
    # Test single clip creation
    if not test_single_clip_creation(ffmpeg_path, png_files, audio_files):
        print("❌ Single clip creation failed. This might be the bottleneck.")
        return
    
    print("\n✅ All tests passed! The video creation process should work.")
    print("If the main script is still slow, the issue might be:")
    print("   1. Processing all 15 clips sequentially")
    print("   2. The concatenation step")
    print("   3. System resources (CPU/memory)")

if __name__ == "__main__":
    main()
