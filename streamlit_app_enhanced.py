import os
import streamlit as st
import tempfile
import time
import logging
import subprocess
import sys
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("paper_explainer")

# Import processors
from processors.text_extractor import extract_text_from_pdf
from processors.llm_processor import generate_slides_content
from processors.marp_converter import convert_to_marp
from processors.audio_generator import generate_audio
from processors.slide_renderer import render_slides
from processors.video_creator import create_video

# Import utils
from utils.ui_components import (
    display_live_progress,
    update_progress,
    display_figures,
    display_slides_preview,
    display_audio_preview,
    display_video_player
)
from utils.file_helpers import save_uploaded_file

# Page config
st.set_page_config(
    page_title="Paper Explainer 📑",
    page_icon="📑",
    layout="wide",
)

# Initialize session state
if "processing_status" not in st.session_state:
    st.session_state.processing_status = {
        "upload": {"status": "waiting", "message": "Waiting for PDF upload"},
        "text_extraction": {"status": "pending", "message": ""},
        "figure_extraction": {"status": "pending", "message": ""},
        "llm_processing": {"status": "pending", "message": ""},
        "markdown_generation": {"status": "pending", "message": ""},
        "audio_generation": {"status": "pending", "message": ""},
        "slide_rendering": {"status": "pending", "message": ""},
        "video_creation": {"status": "pending", "message": ""}
    }

if "progress_details" not in st.session_state:
    st.session_state.progress_details = {}

if "output_paths" not in st.session_state:
    st.session_state.output_paths = {
        "pdf": "",
        "figures_metadata": "",
        "slides_json": "",
        "deck_md": "",
        "audio_dir": "",
        "frames_dir": "",
        "video": ""
    }

if "temp_dir" not in st.session_state:
    st.session_state.temp_dir = tempfile.mkdtemp()

if "processing_started" not in st.session_state:
    st.session_state.processing_started = False

if "processing_complete" not in st.session_state:
    st.session_state.processing_complete = False

# Helper functions
def log_info(message):
    """Log message and update progress details"""
    logger.info(message)

def update_step_status(step_key, status, message=""):
    """Update the status of a processing step"""
    st.session_state.processing_status[step_key] = {
        "status": status,
        "message": message
    }

def extract_figures_with_progress(pdf_path, output_dir):
    """Extract figures with progress tracking"""
    update_step_status("figure_extraction", "processing", "Starting figure extraction...")
    update_progress("figure_extraction", detail="Initializing figure extraction")
    
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Run extract_images_llm.py with progress tracking
        cmd = [sys.executable, "extract_images_llm.py", pdf_path, "--output_dir", output_dir]
        
        update_progress("figure_extraction", detail=f"Running command: {' '.join(cmd)}")
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        page_count = 0
        current_page = 0
        
        # Read output line by line for progress tracking
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                update_progress("figure_extraction", detail=line)
                
                # Parse progress information
                if "Converting PDF pages to images" in line:
                    update_progress("figure_extraction", detail="Converting PDF to images...")
                elif "Rendering pages:" in line and "%" in line:
                    # Extract progress from tqdm output
                    try:
                        # Look for pattern like "4/4 [00:00<00:00, 4.80it/s]"
                        if "/" in line:
                            parts = line.split("/")
                            if len(parts) >= 2:
                                current = int(parts[0].split()[-1])
                                total_part = parts[1].split()[0]
                                total = int(total_part)
                                page_count = total
                                update_progress("figure_extraction", current=current, total=total)
                    except:
                        pass
                elif "Analyzing page_" in line:
                    current_page += 1
                    if page_count > 0:
                        update_progress("figure_extraction", current=current_page, total=page_count)
                elif "Cropping figures:" in line and "%" in line:
                    update_progress("figure_extraction", detail="Cropping extracted figures...")
                elif "Successfully extracted" in line:
                    update_progress("figure_extraction", detail=line)
        
        process.wait()
        
        if process.returncode == 0:
            # Check for metadata file
            figures_metadata_path = os.path.join(output_dir, "figures_metadata.json")
            if os.path.exists(figures_metadata_path):
                # Count figures
                with open(figures_metadata_path, 'r') as f:
                    figures_data = json.load(f)
                figure_count = len(figures_data)
                
                update_step_status("figure_extraction", "complete", f"Extracted {figure_count} figures")
                update_progress("figure_extraction", detail=f"✅ Successfully extracted {figure_count} figures")
                return figures_metadata_path
            else:
                update_step_status("figure_extraction", "complete", "No figures found in PDF")
                update_progress("figure_extraction", detail="No figures found in the PDF")
                return None
        else:
            raise subprocess.CalledProcessError(process.returncode, cmd)
            
    except Exception as e:
        error_msg = f"Figure extraction failed: {str(e)}"
        update_step_status("figure_extraction", "error", error_msg)
        update_progress("figure_extraction", detail=f"❌ {error_msg}")
        return None



def create_video_with_progress(frames_dir, audio_dir, output_path):
    """Create video with progress tracking"""
    update_step_status("video_creation", "processing", "Starting video creation...")
    update_progress("video_creation", detail="Initializing video creation...")
    
    try:
        # Count files for progress tracking
        png_files = sorted(Path(frames_dir).glob("deck.*.png"))
        audio_files = sorted(Path(audio_dir).glob("*.wav"))
        
        total_steps = len(png_files) + 2  # clips + preprocessing + concatenation
        current_step = 0
        
        update_progress("video_creation", total=total_steps, current=current_step)
        
        # Call the video creation function with progress callback
        def progress_callback(step_name, current=None, total=None):
            nonlocal current_step
            if current is not None:
                current_step = current
            else:
                current_step += 1
            update_progress("video_creation", current=current_step, detail=step_name)
        
        success = create_video(frames_dir, audio_dir, output_path, progress_callback)
        
        if success:
            update_step_status("video_creation", "complete", "Video created successfully")
            update_progress("video_creation", detail="✅ Video creation completed")
            return output_path
        else:
            raise Exception("Video creation failed")
            
    except Exception as e:
        error_msg = f"Video creation failed: {str(e)}"
        update_step_status("video_creation", "error", error_msg)
        update_progress("video_creation", detail=f"❌ {error_msg}")
        return None

# Main UI
st.title("Paper Explainer 📑")
st.markdown("This app converts academic papers (PDFs) into concise, narrated video presentations. Upload your PDF to get started!")

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Keys section
    with st.expander("🔑 API Keys", expanded=False):
        gemini_key = st.text_input("Gemini API Key", type="password", help="Required for LLM processing")
        sarvam_key = st.text_input("Sarvam API Key", type="password", help="Required for audio generation")
        
        if gemini_key:
            os.environ["GEMINI_API_KEY"] = gemini_key
        if sarvam_key:
            os.environ["SARVAM_API_KEY"] = sarvam_key
    
    # Processing options
    with st.expander("🔧 Processing Options", expanded=False):
        max_slides = st.number_input("Max slides", min_value=2, max_value=20, value=10)
        slides_only = st.checkbox("Generate slides only (skip audio/video)", value=False)

# File upload
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    st.session_state.processing_status["upload"]["status"] = "complete"
    st.session_state.processing_status["upload"]["message"] = f"Uploaded: {uploaded_file.name}"

# Processing controls
if uploaded_file is not None:
    if not st.session_state.processing_started and not st.session_state.processing_complete:
        start_button = st.button(
            "🚀 Start Processing", 
            type="primary",
            use_container_width=True
        )
    elif st.session_state.processing_started and not st.session_state.processing_complete:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("🔄 Processing in progress...")
        with col2:
            if st.button("⏹️ Stop"):
                st.session_state.processing_started = False
                st.rerun()
    else:
        st.success("✅ Processing completed!")
        if st.button("🔄 Process Another PDF"):
            # Reset session state for new processing
            for key in ["processing_started", "processing_complete", "processing_status", "progress_details", "output_paths"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
else:
    st.info("📄 Please upload a PDF file to get started.")
    start_button = False

# Display progress (only show when processing has started)
if st.session_state.processing_started or st.session_state.processing_complete:
    display_live_progress()

# Start processing
if 'start_button' in locals() and start_button and uploaded_file is not None and not st.session_state.processing_started:
    st.session_state.processing_started = True
    # Initialize session state properly
    st.session_state.processing_complete = False
    st.session_state.processing_status = {
        "upload": {"status": "complete", "message": f"Uploaded: {uploaded_file.name}"},
        "text_extraction": {"status": "pending", "message": ""},
        "figure_extraction": {"status": "pending", "message": ""},
        "llm_processing": {"status": "pending", "message": ""},
        "markdown_generation": {"status": "pending", "message": ""},
        "audio_generation": {"status": "pending", "message": ""},
        "slide_rendering": {"status": "pending", "message": ""},
        "video_creation": {"status": "pending", "message": ""}
    }
    st.session_state.progress_details = {}
    
    # Rerun to show progress immediately
    st.rerun()

# Process the file if processing has started
if st.session_state.processing_started and not st.session_state.processing_complete:
    # Save uploaded file
    pdf_path = save_uploaded_file(uploaded_file, st.session_state.temp_dir)
    st.session_state.output_paths["pdf"] = pdf_path
    
    # Create output directories
    import shutil
    slides_dir = "slides"
    # Clean previous outputs to avoid stale files
    if os.path.exists(slides_dir):
        shutil.rmtree(slides_dir)
    figures_dir = os.path.join(st.session_state.temp_dir, "figures")
    audio_dir = os.path.join(slides_dir, "audio")
    frames_dir = os.path.join(slides_dir, "frames")
    
    os.makedirs(slides_dir, exist_ok=True)
    
    try:
        # Step 1: Extract text
        update_step_status("text_extraction", "processing", "Extracting text from PDF...")
        update_progress("text_extraction", detail="Starting text extraction")
        
        text_content = extract_text_from_pdf(pdf_path)
        char_count = len(text_content)
        
        update_step_status("text_extraction", "complete", f"Extracted {char_count} characters")
        update_progress("text_extraction", detail=f"✅ Extracted {char_count} characters")
        
        # Step 2: Extract figures
        figures_metadata_path = extract_figures_with_progress(pdf_path, figures_dir)
        if figures_metadata_path:
            st.session_state.output_paths["figures_metadata"] = figures_metadata_path
        
        # Step 3: Generate slide content
        update_step_status("llm_processing", "processing", "Generating slide content with LLM...")
        update_progress("llm_processing", detail="Sending content to LLM for processing")
        
        # The generate_slides_content function returns a JSON file path, not the data directly
        slides_json_path = generate_slides_content(
            text_content, 
            figures_metadata_path, 
            max_slides=max_slides
        )
        
        # Load the slides data from the JSON file to get the count
        with open(slides_json_path, 'r', encoding='utf-8') as f:
            slides_data = json.load(f)
        
        slide_count = len(slides_data)
        update_step_status("llm_processing", "complete", f"Generated {slide_count} slides")
        update_progress("llm_processing", detail=f"✅ Generated content for {slide_count} slides")
        
        # Step 4: Create Markdown from existing JSON
        update_step_status("markdown_generation", "processing", "Creating Marp slides...")
        update_progress("markdown_generation", detail="Converting JSON to Marp Markdown format")
        
        # We already have the JSON file from the LLM processor
        st.session_state.output_paths["slides_json"] = slides_json_path
        
        # Convert JSON to Marp markdown
        deck_path = convert_to_marp(slides_json_path)
        st.session_state.output_paths["deck_md"] = deck_path
        
        update_step_status("markdown_generation", "complete", "Marp slides created")
        update_progress("markdown_generation", detail="✅ Created Marp slides")
        
        if not slides_only:
            # Step 5: Generate audio
            update_step_status("audio_generation", "processing", "Starting audio generation...")
            update_progress("audio_generation", detail="Generating audio files using Sarvam AI")
            
            try:
                audio_dir_path = generate_audio(slides_json_path)
                if audio_dir_path:
                    st.session_state.output_paths["audio_dir"] = audio_dir_path
                    # Count audio files
                    audio_files = list(Path(audio_dir_path).glob("*.wav"))
                    update_step_status("audio_generation", "complete", f"Generated {len(audio_files)} audio files")
                    update_progress("audio_generation", detail=f"✅ Generated {len(audio_files)} audio files")
                else:
                    update_step_status("audio_generation", "error", "Audio generation failed")
            except Exception as e:
                update_step_status("audio_generation", "error", f"Audio generation failed: {str(e)}")
                update_progress("audio_generation", detail=f"❌ Audio generation error: {str(e)}")
                audio_dir_path = None
            
            # Step 6: Render slides
            update_step_status("slide_rendering", "processing", "Rendering slide images...")
            update_progress("slide_rendering", detail="Converting slides to PNG images")
            
            frames_dir_path = render_slides(deck_path, frames_dir)
            if frames_dir_path:
                st.session_state.output_paths["frames_dir"] = frames_dir_path
                
                # Count rendered slides
                png_files = list(Path(frames_dir_path).glob("deck.*.png"))
                update_step_status("slide_rendering", "complete", f"Rendered {len(png_files)} slide images")
                update_progress("slide_rendering", detail=f"✅ Rendered {len(png_files)} slide images")
            
            # Step 7: Create video
            if audio_dir_path and frames_dir_path:
                video_path = os.path.join(slides_dir, "video.mp4")
                video_result = create_video_with_progress(frames_dir_path, audio_dir_path, video_path)
                if video_result:
                    st.session_state.output_paths["video"] = video_result
        
        st.session_state.processing_complete = True
        
    except Exception as e:
        st.error(f"Processing failed: {str(e)}")
        logger.error(f"Processing failed: {str(e)}")

# Display results
if st.session_state.processing_complete:
    st.markdown("---")
    st.markdown("## 🎉 Results")
    
    # Create tabs for different outputs
    tabs = ["📊 Summary"]
    
    if st.session_state.output_paths.get("figures_metadata"):
        tabs.append("🖼️ Figures")
    
    if st.session_state.output_paths.get("frames_dir"):
        tabs.append("📋 Slides")
    
    if st.session_state.output_paths.get("audio_dir"):
        tabs.append("🔊 Audio")
    
    if st.session_state.output_paths.get("video"):
        tabs.append("🎬 Video")
    
    tab_objects = st.tabs(tabs)
    
    # Summary tab
    with tab_objects[0]:
        st.markdown("### Processing Summary")
        
        completed_steps = sum(1 for status in st.session_state.processing_status.values() 
                            if status["status"] == "complete")
        total_steps = len(st.session_state.processing_status)
        
        st.metric("Completed Steps", f"{completed_steps}/{total_steps}")
        
        if st.session_state.output_paths.get("video"):
            video_path = st.session_state.output_paths["video"]
            if os.path.exists(video_path):
                size_mb = os.path.getsize(video_path) / (1024 * 1024)
                st.metric("Video Size", f"{size_mb:.1f} MB")
    
    # Figures tab
    tab_idx = 1
    if st.session_state.output_paths.get("figures_metadata"):
        with tab_objects[tab_idx]:
            display_figures(st.session_state.output_paths["figures_metadata"])
        tab_idx += 1
    
    # Slides tab
    if st.session_state.output_paths.get("frames_dir"):
        with tab_objects[tab_idx]:
            display_slides_preview(st.session_state.output_paths["frames_dir"])
        tab_idx += 1
    
    # Audio tab
    if st.session_state.output_paths.get("audio_dir"):
        with tab_objects[tab_idx]:
            display_audio_preview(st.session_state.output_paths["audio_dir"])
        tab_idx += 1
    
    # Video tab
    if st.session_state.output_paths.get("video"):
        with tab_objects[tab_idx]:
            display_video_player(st.session_state.output_paths["video"])

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit • [GitHub](https://github.com/your-repo)")
