#!/usr/bin/env python3
"""
Test script to run the full video creation process with timing and progress monitoring.
This will help identify if there are any bottlenecks in the current implementation.
"""

import subprocess
import shutil
import tempfile
import time
from pathlib import Path
import os

def create_test_video():
    """Create a new video using the same logic as the main script."""
    print("🎬 Testing Full Video Creation Process")
    print("=" * 50)
    
    frames_dir = "/home/ragha/code/paper_agent_2/slides/frames"
    audio_dir = "/home/ragha/code/paper_agent_2/slides/audio"
    output_video_path = "/home/ragha/code/paper_agent_2/slides/test_video.mp4"
    
    # Check for ffmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        print("❌ Error: ffmpeg not found.")
        return False

    temp_dir = Path(tempfile.mkdtemp(prefix="video_temp_"))
    total_start_time = time.time()
    
    try:
        print(f"🔧 Using temporary directory: {temp_dir}")
        
        # Get files
        png_files = sorted(Path(frames_dir).glob("deck.*.png"))
        audio_files = sorted(Path(audio_dir).glob("*.wav"))
        
        print(f"📁 Found {len(png_files)} PNG files and {len(audio_files)} audio files")
        
        if not png_files or not audio_files:
            print("❌ Missing required files")
            return False
        
        # Step 1: Pre-process audio files
        print("\n🔧 Step 1: Pre-processing audio files...")
        audio_start_time = time.time()
        standardized_audio_files = []
        
        for i, audio_file in enumerate(audio_files, 1):
            print(f"   Processing audio {i}/{len(audio_files)}: {audio_file.name}")
            standardized_path = temp_dir / f"std_{audio_file.name}"
            
            standardize_cmd = [
                ffmpeg_path,
                "-i", str(audio_file),
                "-acodec", "pcm_s16le",
                "-ar", "44100",
                "-ac", "2",
                "-y",  # Overwrite
                str(standardized_path)
            ]
            
            file_start = time.time()
            result = subprocess.run(standardize_cmd, capture_output=True, text=True)
            file_time = time.time() - file_start
            
            if result.returncode != 0:
                print(f"   ❌ Failed to process {audio_file.name}: {result.stderr}")
                return False
            
            print(f"   ✅ Processed in {file_time:.2f}s")
            standardized_audio_files.append(standardized_path)
        
        audio_total_time = time.time() - audio_start_time
        print(f"✅ Audio preprocessing completed in {audio_total_time:.2f}s")
        
        # Step 2: Create individual video clips
        print(f"\n🎥 Step 2: Creating {len(standardized_audio_files)} individual video clips...")
        clips_start_time = time.time()
        individual_clips = []
        
        for i, audio_file in enumerate(standardized_audio_files):
            slide_num = i + 1
            print(f"   Creating clip {slide_num}/{len(standardized_audio_files)}")
            
            if len(png_files) <= i:
                print(f"   ⚠️  Missing PNG for slide {slide_num}. Skipping.")
                continue
                
            png_file = png_files[i]
            clip_output_path = temp_dir / f"clip_{slide_num:02d}.mp4"
            
            # Get audio duration
            ffprobe_path = shutil.which("ffprobe") or ffmpeg_path
            duration_cmd = [ffprobe_path, "-i", str(audio_file), "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"]
            
            try:
                duration_output = subprocess.check_output(duration_cmd, timeout=30).decode("utf-8").strip()
                duration = float(duration_output)
            except Exception as e:
                print(f"   ❌ Failed to get duration for {audio_file.name}: {e}")
                continue
            
            # Create video clip
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
                "-y",  # Overwrite
                str(clip_output_path)
            ]
            
            clip_start = time.time()
            result = subprocess.run(clip_cmd, capture_output=True, text=True)
            clip_time = time.time() - clip_start
            
            if result.returncode != 0:
                print(f"   ❌ Failed to create clip {slide_num}: {result.stderr}")
                continue
            
            print(f"   ✅ Clip {slide_num} created in {clip_time:.2f}s ({duration:.1f}s audio)")
            individual_clips.append(clip_output_path)
        
        clips_total_time = time.time() - clips_start_time
        print(f"✅ Individual clips created in {clips_total_time:.2f}s")
        
        if not individual_clips:
            print("❌ No clips were created successfully")
            return False
        
        # Step 3: Concatenate clips
        print(f"\n🔗 Step 3: Concatenating {len(individual_clips)} clips...")
        concat_start_time = time.time()
        
        concat_file_list_path = temp_dir / "concat_clips.txt"
        with open(concat_file_list_path, "w", encoding="utf-8") as f:
            for clip_path in individual_clips:
                f.write(f"file '{clip_path}'\n")
        
        final_concat_cmd = [
            ffmpeg_path, 
            "-f", "concat", 
            "-safe", "0", 
            "-i", str(concat_file_list_path),
            "-c", "copy", 
            "-y",  # Overwrite
            output_video_path
        ]
        
        print(f"   Concatenating to: {output_video_path}")
        result = subprocess.run(final_concat_cmd, capture_output=True, text=True)
        concat_time = time.time() - concat_start_time
        
        if result.returncode != 0:
            print(f"❌ Concatenation failed: {result.stderr}")
            return False
        
        print(f"✅ Concatenation completed in {concat_time:.2f}s")
        
        # Check final video
        if Path(output_video_path).exists():
            size = Path(output_video_path).stat().st_size
            total_time = time.time() - total_start_time
            print(f"\n🎉 SUCCESS! Video created: {size} bytes ({size/1024/1024:.2f} MB)")
            print(f"⏱️  Total time: {total_time:.2f}s")
            print(f"   - Audio preprocessing: {audio_total_time:.2f}s ({audio_total_time/total_time*100:.1f}%)")
            print(f"   - Clip creation: {clips_total_time:.2f}s ({clips_total_time/total_time*100:.1f}%)")
            print(f"   - Concatenation: {concat_time:.2f}s ({concat_time/total_time*100:.1f}%)")
            return True
        else:
            print("❌ Video file was not created")
            return False
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
        
    finally:
        print(f"🧹 Cleaning up temporary directory: {temp_dir}")
        shutil.rmtree(temp_dir)

def main():
    """Run the test."""
    success = create_test_video()
    if success:
        print("\n✅ Video creation process is working correctly!")
        print("If the main script seems slow, it might be due to:")
        print("   1. Running without progress indicators")
        print("   2. System load during processing")
        print("   3. Different ffmpeg settings or error handling")
    else:
        print("\n❌ Video creation process failed. Check the errors above.")

if __name__ == "__main__":
    main()
