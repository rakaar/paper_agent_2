import sys
import os
import json
import subprocess
import shutil
import tempfile
from pathlib import Path
import time

from pdf2json import call_llm

# Try to import pptx and provide a helpful error message if it's not installed.
try:
    import pptx
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    from pptx.enum.shapes import PP_PLACEHOLDER_TYPE
except ImportError:
    print("Error: The 'python-pptx' library is required. Please install it by running:")
    print("pip install python-pptx")
    sys.exit(1)

# Import SarvamAI for TTS
try:
    from sarvamai import SarvamAI
    from sarvamai.play import save as sarvam_save # Rename to avoid conflict with os.save
except ImportError:
    print("Error: The 'sarvamai' library is required for Text-to-Speech. Please install it by running:")
    print("pip install sarvamai")
    sys.exit(1)

# Sarvam API Key (read from environment variable)
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
if not SARVAM_API_KEY:
    print("Error: SARVAM_API_KEY environment variable not set.")
    sys.exit(1)

def create_presentation(slides_data: list, output_filename: str):
    """Creates a PowerPoint presentation from slide data."""
    prs = pptx.Presentation()

    # Find a suitable layout with a body placeholder
    content_layout = None
    for layout_idx, layout in enumerate(prs.slide_layouts):
        for placeholder in layout.placeholders:
            if placeholder.is_placeholder and placeholder.placeholder_format.type == PP_PLACEHOLDER_TYPE.BODY:
                content_layout = layout
                print(f"Found suitable layout at index {layout_idx} with a BODY placeholder.")
                break
        if content_layout:
            break

    if content_layout is None:
        print("Warning: No slide layout with a BODY placeholder found. Using default layout 0.")
        content_layout = prs.slide_layouts[0] # Fallback to a blank layout

    print(f"Creating presentation '{output_filename}.pptx'...")
    for i, slide_info in enumerate(slides_data):
        slide = prs.slides.add_slide(content_layout)
        
        # Safely get title and content, providing defaults if keys are missing
        title = slide_info.get("title", f"Slide {i+1}")
        content = slide_info.get("content", "No content provided.")

        # If content is a list, join it into a single string
        if isinstance(content, list):
            content = "\n".join(content)

        # Set the title
        # Assuming the first placeholder is the title for most layouts
        if slide.shapes.title:
            slide.shapes.title.text = title
        else:
            print(f"Warning: Slide {i+1} has no title placeholder. Title not set.")
        
        # Find the body placeholder
        body_shape = None
        for shape in slide.placeholders:
            if shape.is_placeholder and shape.placeholder.format.type == PP_PLACEHOLDER_TYPE.BODY:
                body_shape = shape
                break
        
        if body_shape is None:
            print(f"Warning: Slide {i+1} could not find a suitable body placeholder. Content might not be added.")
            continue

        tf = body_shape.text_frame
        tf.clear() # Clear existing text (like "Click to add text")
        
        p = tf.paragraphs[0]
        p.text = content
        p.font.size = Pt(18)
        p.alignment = PP_ALIGN.LEFT

    prs.save(f"{output_filename}.pptx")
    print(f"Successfully saved presentation: {output_filename}.pptx")

def save_audio_script(slides_data: list, output_filename: str):
    """Saves the audio narration script to a text file."""
    script_filename = f"{output_filename}_audio_script.txt"
    print(f"Creating audio script '{script_filename}'...")
    with open(script_filename, "w", encoding="utf-8") as f:
        for i, slide_info in enumerate(slides_data):
            slide_num = slide_info.get("slide number", i + 1)
            title = slide_info.get("title", "Untitled Slide")
            audio_text = slide_info.get("audio", "No narration provided.")
            
            f.write(f"--- Slide {slide_num}: {title} ---\n")
            f.write(f"{audio_text}\n\n")
    print(f"Successfully saved audio script: {script_filename}")

def save_slides_json(slides_data: list, output_filename: str):
    """Saves the slides data as a JSON file."""
    json_filename = f"{output_filename}_slides_plan.json"
    print(f"Creating slides plan JSON '{json_filename}'...")
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(slides_data, f, indent=2)
    print(f"Successfully saved slides plan JSON: {json_filename}")

def generate_audio_files(slides_data: list, output_dir: str):
    """Generates audio files from slide narration using Sarvam TTS."""
    print("Generating audio files from slide narration...")
    os.makedirs(output_dir, exist_ok=True)
    client = SarvamAI(api_subscription_key=SARVAM_API_KEY)

    for i, slide_info in enumerate(slides_data):
        audio_text = slide_info.get("audio", "")
        # Use 1-based indexing for slide numbers in filenames
        slide_num = slide_info.get("slide number", i + 1)
        
        if not audio_text:
            print(f"  Skipping audio generation for Slide {slide_num}: No narration text provided.")
            continue

        try:
            print(f"  Generating audio for Slide {slide_num}...")
            audio = client.text_to_speech.convert(
                text=audio_text,
                target_language_code="en-IN",
                model="bulbul:v2",
                speaker="anushka"
            )
            # Save audio files as slide01.wav, slide02.wav, etc.
            audio_file_path = os.path.join(output_dir, f"slide{slide_num:02d}.wav")
            sarvam_save(audio, audio_file_path)
            print(f"  Successfully saved audio for Slide {slide_num} to {audio_file_path}")
        except Exception as e:
            print(f"  Error generating audio for Slide {slide_num}: {e}")

    print("Audio generation complete.")

def create_video_with_ffmpeg(frames_dir: str, audio_dir: str, output_video_path: str):
    """Creates a video from PNG frames and audio files using ffmpeg."""
    print("Creating video using ffmpeg...")
    
    # Check for ffmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        print("Error: ffmpeg not found. Please install ffmpeg.")
        return

    temp_dir = Path(tempfile.mkdtemp(prefix="video_temp_"))
    try:
        # Add a small delay to ensure files are written to disk
        time.sleep(1)

        if not Path(frames_dir).exists():
            print(f"Error: Frames directory does not exist: {frames_dir}")
            return

        print(f"  Contents of frames directory ({frames_dir}):")
        for item in os.listdir(frames_dir):
            print(f"    - {item}")

        # Glob for PNG files, which marp-cli names `deck.001.png`, `deck.002.png`, etc.
        png_files = sorted(Path(frames_dir).glob("deck.*.png"))
        audio_files = sorted(Path(audio_dir).glob("*.wav"))

        print(f"  PNG files found by glob: {png_files}")

        if not png_files:
            print("Error: No PNG files found in frames directory.")
            return
        if not audio_files:
            print("Error: No audio files found for video creation.")
            return

        # Step 1: Pre-process audio files to a standard format to avoid ffmpeg errors
        print("  Pre-processing audio files...")
        standardized_audio_files = []
        for audio_file in audio_files:
            standardized_path = temp_dir / f"std_{audio_file.name}"
            standardize_cmd = [
                ffmpeg_path,
                "-i", str(audio_file),
                "-acodec", "pcm_s16le", # Standard 16-bit PCM
                "-ar", "44100", # 44.1kHz sample rate
                "-ac", "2", # Stereo
                str(standardized_path)
            ]
            subprocess.run(standardize_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            standardized_audio_files.append(standardized_path)
        print("  Audio pre-processing complete.")

        # Step 2: Create individual video clips (image + audio) for each slide
        individual_clips = []
        for i, audio_file in enumerate(standardized_audio_files):
            slide_num = i + 1
            if len(png_files) <= i:
                print(f"Warning: Missing PNG for slide {slide_num}. Skipping video creation for this slide.")
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
            print(f"  Executing ffmpeg clip command: {' '.join(clip_cmd)}")
            subprocess.run(clip_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            individual_clips.append(clip_output_path)
        
        if not individual_clips:
            print("Error: No individual video clips were created.")
            return

        # Step 2: Concatenate individual video clips
        print("  Concatenating individual video clips...")
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
            output_video_path
        ]
        print(f"  Executing ffmpeg concat command: {' '.join(final_concat_cmd)}")
        subprocess.run(final_concat_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Successfully created video: {output_video_path}")

    finally:
        shutil.rmtree(temp_dir)

def main():
    """Main function to drive the script."""
    if len(sys.argv) < 2:
        print("Usage: python txt2slides.py <file1.txt> [file2.txt] ...")
        sys.exit(1)

    input_files = sys.argv[1:]
    
    print(f"Reading and combining text from: {', '.join(input_files)}")
    
    combined_text = []
    for file_path in input_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                combined_text.append(f.read())
        except FileNotFoundError:
            print(f"Error: File not found at '{file_path}'. Skipping.")
            continue
    
    if not combined_text:
        print("No valid files were found. Exiting.")
        sys.exit(1)

    full_text = "\n\n---\n\n".join(combined_text)

    # Calculate max_slides based on the number of input files
    max_slides = len(input_files) * 2 

    system_prompt = "You are an expert instructional designer. Your task is to convert the provided text into a slide deck for a presentation. You must respond with only a valid JSON array of slide objects, with no other text or explanation."
    
    user_prompt = f"""
Please break the following text into exactly {max_slides} slides. Each slide must be a JSON object with these exact keys: "slide number", "title", "content", and "audio".
- "slide number": An integer for the slide order.
- "title": A concise title for the slide.
- "content": Keep this very minimal, using only a few bullet points or a very short paragraph. This is for visual cues only.
- "audio": This should contain the full, detailed narration for the slide, suitable for text-to-speech. Maximize information transfer here.

Do not include any text, prose, or markdown formatting outside of the main JSON array.

--- TEXT TO CONVERT ---
{full_text}
"""

    print("Sending content to the language model for processing...")
    try:
        llm_response_str = call_llm(system_prompt, user_prompt)
        
        # Clean the response to ensure it's just the JSON array
        # The model sometimes wraps the JSON in ```json ... ```
        if llm_response_str.strip().startswith("```json"):
            llm_response_str = llm_response_str.strip()[7:-3].strip()

        slides_data = json.loads(llm_response_str)
        print(f"LLM returned slides_data: {json.dumps(slides_data, indent=2)}") # Debug print

    except json.JSONDecodeError:
        print("\n--- ERROR: Failed to decode JSON from LLM response. ---")
        print("The model did not return a valid JSON string.")
        print("Raw response received:\n")
        print(llm_response_str)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during LLM call or processing: {e}")
        sys.exit(1)

    print("LLM response received and parsed successfully.")
    
    # Define output directories and filenames
    base_output_filename, _ = os.path.splitext(input_files[0])
    slides_dir = Path("slides")
    slides_dir.mkdir(parents=True, exist_ok=True)

    json_output_path = slides_dir / f"{base_output_filename}_slides_plan.json"
    marp_md_path = slides_dir / "deck.md"
    audio_output_dir = slides_dir / "audio"
    frames_output_dir = slides_dir / "frames"
    # Marp CLI needs a dummy file path in the target directory for image sequence output
    frames_output_path_template = frames_output_dir / "deck.png"
    video_output_path = slides_dir / "video.mp4"

    # Save slides data as JSON
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(slides_data, f, indent=2)
    print(f"Successfully saved slides plan JSON: {json_output_path}")

    # Generate Marp Markdown
    print("Generating Marp Markdown...")
    try:
        subprocess.run(
            [
                sys.executable, 
                "json2marp.py", 
                str(json_output_path), 
                "--out", str(marp_md_path)
            ],
            check=True
        )
        print(f"Successfully created Marp Markdown: {marp_md_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error generating Marp Markdown: {e}")
        print(f"Stdout: {e.stdout.decode()}")
        print(f"Stderr: {e.stderr.decode()}")
        sys.exit(1)

    # Generate audio files
    generate_audio_files(slides_data, str(audio_output_dir)) 

    # Render Marp Markdown to PNG frames
    print("Rendering Marp Markdown to PNG frames...")
    frames_output_dir.mkdir(parents=True, exist_ok=True) # Ensure frames directory exists
    try:
        # Use npx to run marp-cli
        subprocess.run(
            [
                "npx", "marp", 
                str(marp_md_path),
                "--images", "png",
                "--image-scale", "2",
                "--allow-local-files",
                # Provide a dummy file path; marp-cli will use its basename for the sequence
                "--output", str(frames_output_path_template)
            ],
            check=True
        )
        print(f"Successfully rendered PNG frames to: {frames_output_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Error rendering Marp Markdown to PNGs: {e}")
        print(f"Stdout: {e.stdout.decode()}")
        print(f"Stderr: {e.stderr.decode()}")
        sys.exit(1)

    # Build video from PNG frames and audio
    print("Building video from PNG frames and audio...")
    try:
        # Call create_video_with_ffmpeg directly
        create_video_with_ffmpeg(str(frames_output_dir), str(audio_output_dir), str(video_output_path))
        print(f"Successfully created video: {video_output_path}")
    except Exception as e:
        print(f"Error building video: {e}")
        # Also print stdout and stderr for more context on ffmpeg errors
        if isinstance(e, subprocess.CalledProcessError):
            print(f"ffmpeg stdout: {e.stdout.decode() if e.stdout else 'N/A'}")
            print(f"ffmpeg stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
        sys.exit(1)

    print("\nAll tasks completed.")

if __name__ == "__main__":
    main()