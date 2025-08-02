import os
import sys
import subprocess
import shutil
import time
import tempfile
from pathlib import Path

def create_video(frames_dir, audio_dir, output_path=None, progress_callback=None):
    """
    Create a video from PNG frames and audio files using ffmpeg
    
    Args:
        frames_dir (str): Path to directory containing PNG frames
        audio_dir (str): Path to directory containing audio files
        progress_callback (callable, optional): Function to call for progress updates
        
    Returns:
        str: Path to the generated video file, or None if failed
    """
    def update_progress(message, current=None, total=None):
        if progress_callback:
            progress_callback(message, current, total)
        else:
            print(message)
    # Determine output video path
    if output_path is None:
        output_dir = Path("slides")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_video_path = output_dir / "video.mp4"
    else:
        output_video_path = Path(output_path)
        output_video_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check for ffmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg not found. Please install ffmpeg.")

    temp_dir = Path(tempfile.mkdtemp(prefix="video_temp_"))
    try:
        # Add a small delay to ensure files are written to disk
        time.sleep(1)

        frames_dir_path = Path(frames_dir)
        audio_dir_path = Path(audio_dir)
        
        if not frames_dir_path.exists():
            raise FileNotFoundError(f"Frames directory does not exist: {frames_dir}")

        # Glob for PNG files, which marp-cli names `deck.001.png`, `deck.002.png`, etc.
        png_files = sorted(frames_dir_path.glob("deck.*.png"))
        audio_files = sorted(audio_dir_path.glob("*.wav"))

        if not png_files:
            raise FileNotFoundError(f"No PNG files found in frames directory: {frames_dir}")
        if not audio_files:
            raise FileNotFoundError(f"No audio files found in audio directory: {audio_dir}")

        # Step 1: Pre-process audio files to a standard format to avoid ffmpeg errors
        update_progress("Pre-processing audio files...")
        standardized_audio_files = []
        for i, audio_file in enumerate(audio_files):
            update_progress(f"Processing audio file {i+1}/{len(audio_files)}", i, len(audio_files))
            standardized_path = temp_dir / f"std_{audio_file.name}"
            standardize_cmd = [
                ffmpeg_path,
                "-i", str(audio_file),
                "-acodec", "pcm_s16le", # Standard 16-bit PCM
                "-ar", "44100", # 44.1kHz sample rate
                "-ac", "2", # Stereo
                str(standardized_path)
            ]
            result = subprocess.run(standardize_cmd, check=False, capture_output=True, text=True)
            if result.returncode != 0:
                error_details = []
                error_details.append(f"Audio standardization failed for {audio_file.name}")
                error_details.append(f"FFmpeg command: {' '.join(standardize_cmd)}")
                if result.stdout:
                    error_details.append(f"STDOUT: {result.stdout.strip()}")
                if result.stderr:
                    error_details.append(f"STDERR: {result.stderr.strip()}")
                
                # Common ffmpeg audio issues
                stderr_lower = result.stderr.lower() if result.stderr else ""
                if "no space left" in stderr_lower:
                    error_details.append("SOLUTION: Free up disk space")
                elif "permission denied" in stderr_lower:
                    error_details.append("SOLUTION: Check file permissions for input/output files")
                elif "invalid data found" in stderr_lower:
                    error_details.append("SOLUTION: The audio file may be corrupted")
                elif "codec not found" in stderr_lower:
                    error_details.append("SOLUTION: Install additional ffmpeg codecs")
                
                raise Exception("FFmpeg audio preprocessing failed:\n" + "\n".join(error_details))
            standardized_audio_files.append(standardized_path)
        update_progress("Audio pre-processing complete")

        # Step 2: Create individual video clips (image + audio) for each slide
        update_progress("Creating individual video clips...")
        individual_clips = []
        for i, audio_file in enumerate(standardized_audio_files):
            slide_num = i + 1
            update_progress(f"Creating clip {slide_num}/{len(standardized_audio_files)}", i, len(standardized_audio_files))
            
            if len(png_files) <= i:
                update_progress(f"Warning: Missing PNG for slide {slide_num}. Skipping.")
                continue
            png_file = png_files[i]
            
            clip_output_path = temp_dir / f"clip_{slide_num:02d}.mp4"
            
            # Get audio duration from the standardized file
            ffprobe_path = shutil.which("ffprobe") or ffmpeg_path # Use ffprobe if available
            duration_cmd = [ffprobe_path, "-i", str(audio_file), "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"]
            duration_output = subprocess.check_output(duration_cmd).decode("utf-8").strip()
            duration = float(duration_output)

            # Command to create a video clip for one slide
            clip_cmd = [
                ffmpeg_path, 
                "-loop", "1", 
                "-i", str(png_file),
                "-i", str(audio_file),
                "-c:v", "libx264", 
                "-tune", "stillimage", # Optimize for still images
                "-c:a", "aac", 
                "-b:a", "192k", # Audio bitrate
                "-pix_fmt", "yuv420p", 
                "-shortest", 
                "-t", str(duration), # Set video duration to audio duration
                str(clip_output_path)
            ]
            result = subprocess.run(clip_cmd, check=False, capture_output=True, text=True)
            if result.returncode != 0:
                error_details = []
                error_details.append(f"Video clip creation failed for slide {slide_num}")
                error_details.append(f"PNG file: {png_file}")
                error_details.append(f"Audio file: {audio_file}")
                error_details.append(f"FFmpeg command: {' '.join(clip_cmd)}")
                if result.stdout:
                    error_details.append(f"STDOUT: {result.stdout.strip()}")
                if result.stderr:
                    error_details.append(f"STDERR: {result.stderr.strip()}")
                
                # Common ffmpeg video creation issues
                stderr_lower = result.stderr.lower() if result.stderr else ""
                if "no such file" in stderr_lower:
                    error_details.append("SOLUTION: Check that PNG and audio files exist")
                elif "invalid data found" in stderr_lower:
                    error_details.append("SOLUTION: PNG or audio file may be corrupted")
                elif "encoder not found" in stderr_lower or "codec not found" in stderr_lower:
                    error_details.append("SOLUTION: Install full ffmpeg with libx264 codec")
                elif "permission denied" in stderr_lower:
                    error_details.append("SOLUTION: Check file permissions")
                elif "no space left" in stderr_lower:
                    error_details.append("SOLUTION: Free up disk space")
                elif "duration too small" in stderr_lower:
                    error_details.append("SOLUTION: Audio file duration might be invalid")
                
                raise Exception("FFmpeg video clip creation failed:\n" + "\n".join(error_details))
            individual_clips.append(clip_output_path)
        
        if not individual_clips:
            update_progress("Error: No individual video clips were created")
            return None

        # Step 3: Concatenate individual video clips
        update_progress("Concatenating individual video clips...")
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
            str(output_video_path)
        ]
        result = subprocess.run(final_concat_cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            error_details = []
            error_details.append(f"Video concatenation failed")
            error_details.append(f"Concat file: {concat_file_list_path}")
            error_details.append(f"Output path: {output_video_path}")
            error_details.append(f"FFmpeg command: {' '.join(final_concat_cmd)}")
            if result.stdout:
                error_details.append(f"STDOUT: {result.stdout.strip()}")
            if result.stderr:
                error_details.append(f"STDERR: {result.stderr.strip()}")
            
            # Common ffmpeg concatenation issues
            stderr_lower = result.stderr.lower() if result.stderr else ""
            if "no such file" in stderr_lower:
                error_details.append("SOLUTION: Check that all clip files exist")
            elif "invalid data found" in stderr_lower:
                error_details.append("SOLUTION: One or more video clips may be corrupted")
            elif "permission denied" in stderr_lower:
                error_details.append("SOLUTION: Check write permissions for output directory")
            elif "no space left" in stderr_lower:
                error_details.append("SOLUTION: Free up disk space")
            elif "unsafe file name" in stderr_lower:
                error_details.append("SOLUTION: File paths in concat list may have issues")
            
            raise Exception("FFmpeg video concatenation failed:\n" + "\n".join(error_details))
        
        update_progress(f"Video creation completed: {output_video_path}")
        return str(output_video_path)

    except Exception as e:
        update_progress(f"Error creating video: {str(e)}")
        return None
    finally:
        shutil.rmtree(temp_dir)
