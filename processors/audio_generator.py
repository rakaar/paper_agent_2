import os
import json
from pathlib import Path
from sarvamai import SarvamAI
from sarvamai.play import save as sarvam_save

def generate_single_audio(text, output_path):
    """
    Generate a single audio file from text using Sarvam AI TTS
    
    Args:
        text (str): Text to convert to speech
        output_path (str): Path where the audio file should be saved
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Verify that the SARVAM_API_KEY is set
        SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
        if not SARVAM_API_KEY:
            print("Warning: SARVAM_API_KEY environment variable not set")
            return False
        
        if not text.strip():
            print("Warning: No text provided for audio generation")
            return False
        
        # Initialize Sarvam AI client
        client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
        
        # Generate audio
        audio = client.text_to_speech.convert(
            text=text,
            target_language_code="en-IN",
            model="bulbul:v2",
            speaker="anushka"
        )
        
        # Save the audio file
        sarvam_save(audio, output_path)
        return True
        
    except Exception as e:
        print(f"Error generating audio: {str(e)}")
        return False

def generate_audio(slides_json_path, output_dir):
    """
    Generate audio files for each slide using Sarvam AI TTS
    
    Args:
        slides_json_path (str): Path to the slides plan JSON file
        
    Returns:
        str: Path to the directory containing generated audio files
    """
    # Verify that the SARVAM_API_KEY is set
    SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
    if not SARVAM_API_KEY:
        raise ValueError("SARVAM_API_KEY environment variable not set")
    
    # Use the provided output directory
    audio_dir = Path(output_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Load slides data from JSON
        with open(slides_json_path, 'r', encoding='utf-8') as f:
            slides_data = json.load(f)
        
        # Initialize Sarvam AI client
        client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
        
        # Generate audio for each slide
        for i, slide_info in enumerate(slides_data):
            audio_text = slide_info.get("audio", "")
            # Use 1-based indexing for slide numbers in filenames
            slide_num = slide_info.get("slide number", i + 1)
            
            if not audio_text:
                print(f"  Skipping audio generation for Slide {slide_num}: No narration text provided.")
                continue
            
            print(f"  Generating audio for Slide {slide_num}...")
            audio = client.text_to_speech.convert(
                text=audio_text,
                target_language_code="en-IN",
                model="bulbul:v2",
                speaker="anushka"
            )
            
            # Save audio files as slide01.wav, slide02.wav, etc.
            audio_file_path = audio_dir / f"slide{slide_num:02d}.wav"
            sarvam_save(audio, str(audio_file_path))
            print(f"  Successfully saved audio for Slide {slide_num} to {audio_file_path}")
        
        return str(audio_dir)
        
    except Exception as e:
        raise Exception(f"Error generating audio: {str(e)}")
