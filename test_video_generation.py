import logging
import sys
from pathlib import Path

# Add the project root to the Python path to allow importing processor modules
project_root = Path(__file__).parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from processors.video_creator import create_video

# --- Configuration ---
FRAMES_DIR = "slides/frames"
AUDIO_DIR = "slides/audio"
OUTPUT_VIDEO_PATH = "slides/test_video_output.mp4"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("video_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def progress_logger(message, current=None, total=None):
    """A simple logger to be used as a callback."""
    if current is not None and total is not None:
        # The video_creator script might be 0-indexed, so we show 1-based progress
        progress_step = current + 1 if isinstance(current, int) else current
        logging.info(f"{message} - {progress_step}/{total}")
    else:
        logging.info(message)

def main():
    """
    Main function to run the video creation test.
    """
    logging.info("--- Starting Video Generation Test ---")

    # Get absolute paths from the current working directory
    base_dir = Path.cwd()
    frames_path = base_dir / FRAMES_DIR
    audio_path = base_dir / AUDIO_DIR
    output_path = base_dir / OUTPUT_VIDEO_PATH

    logging.info(f"Using frames directory: {frames_path}")
    logging.info(f"Using audio directory: {audio_path}")
    logging.info(f"Output video will be saved to: {output_path}")

    # --- Verification Step ---
    if not frames_path.exists() or not frames_path.is_dir():
        logging.error(f"Frames directory not found at: {frames_path}")
        return
    if not audio_path.exists() or not audio_path.is_dir():
        logging.error(f"Audio directory not found at: {audio_path}")
        return

    num_frames = len(list(frames_path.glob("*.png")))
    num_audio = len(list(audio_path.glob("*.wav")))

    logging.info(f"Found {num_frames} image frames.")
    logging.info(f"Found {num_audio} audio files.")

    if num_frames == 0 or num_audio == 0:
        logging.error("Missing frames or audio files. Cannot proceed.")
        return
    
    if num_frames != num_audio:
        logging.warning(
            f"Mismatch between frame count ({num_frames}) and audio count ({num_audio}). "
            f"The video will be generated using the smaller of the two counts."
        )

    # --- Run Video Creation ---
    try:
        logging.info("Calling create_video function...")
        video_file_path = create_video(
            frames_dir=str(frames_path),
            audio_dir=str(audio_path),
            output_path=str(output_path),
            progress_callback=progress_logger
        )

        if video_file_path and Path(video_file_path).exists():
            logging.info(f"\n--- SUCCESS! ---")
            logging.info(f"Video successfully created at: {video_file_path}")
        else:
            logging.error(f"\n--- FAILURE! ---")
            logging.error("Video creation failed. Check the logs above for FFmpeg errors.")

    except Exception as e:
        logging.error(f"\n--- An unexpected error occurred ---", exc_info=True)

if __name__ == "__main__":
    main()
