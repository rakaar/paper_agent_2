import os
import streamlit as st
import tempfile
import time
import logging
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

# Helper function to log to both console and session state
def log_info(message):
    logger.info(message)
    if "logs" not in st.session_state:
        st.session_state.logs = []
    st.session_state.logs.append(f"{time.strftime('%H:%M:%S')} - INFO - {message}")
    # Keep only the last 100 logs
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[-100:]

# Import processors
from processors.text_extractor import extract_text_from_pdf
from processors.figure_extractor import extract_figures
from processors.llm_processor import generate_slides_content
from processors.marp_converter import convert_to_marp
from processors.audio_generator import generate_audio
from processors.slide_renderer import render_slides
from processors.video_creator import create_video

# Import utils
from utils.ui_components import (
    step_header, 
    processing_status,
    display_figures,
    display_slides_preview,
    display_audio_preview,
    display_video_player
)
from utils.file_helpers import save_uploaded_file

# Page config
st.set_page_config(
    page_title="Paper Explainer",
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

if "output_paths" not in st.session_state:
    st.session_state.output_paths = {
        "pdf": "",
        "figures_metadata": "",
        "slides_json": "",
        "marp_md": "",
        "audio_dir": "",
        "frames_dir": "",
        "video": ""
    }

if "temp_dir" not in st.session_state:
    st.session_state.temp_dir = tempfile.mkdtemp()

if "processing_complete" not in st.session_state:
    st.session_state.processing_complete = False

if "processing_started" not in st.session_state:
    st.session_state.processing_started = False
    
if "logs" not in st.session_state:
    st.session_state.logs = []

# Main app header
st.title("Paper Explainer 📑")
st.markdown("""
This app converts academic papers (PDFs) into concise, narrated video presentations.
Upload your PDF to get started!
""")

# File uploader
uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

# API key inputs
with st.expander("API Keys"):
    gemini_api_key = st.text_input("Gemini API Key", type="password", value=os.environ.get("GEMINI_API_KEY", ""))
    sarvam_api_key = st.text_input("Sarvam API Key", type="password", value=os.environ.get("SARVAM_API_KEY", ""))
    
    if gemini_api_key:
        os.environ["GEMINI_API_KEY"] = gemini_api_key
    if sarvam_api_key:
        os.environ["SARVAM_API_KEY"] = sarvam_api_key

# Process settings
with st.expander("Process Settings"):
    max_slides = st.number_input("Maximum number of slides", min_value=4, max_value=20, value=10)
    slides_only = st.checkbox("Generate slides only (skip audio and video)", value=False)

# Progress tracking
st.markdown("## Processing Status")
col1, col2 = st.columns(2)

with col1:
    step_header("1. Upload PDF", st.session_state.processing_status["upload"]["status"])
    step_header("2. Extract Text", st.session_state.processing_status["text_extraction"]["status"])
    step_header("3. Extract Figures", st.session_state.processing_status["figure_extraction"]["status"])
    step_header("4. Generate Slide Content", st.session_state.processing_status["llm_processing"]["status"])
    
with col2:
    step_header("5. Create Markdown Slides", st.session_state.processing_status["markdown_generation"]["status"])
    step_header("6. Generate Audio Narration", st.session_state.processing_status["audio_generation"]["status"])
    step_header("7. Render Slide Images", st.session_state.processing_status["slide_rendering"]["status"])
    step_header("8. Create Final Video", st.session_state.processing_status["video_creation"]["status"])

# Debug log expander
with st.expander("Debug Logs"):
    if st.session_state.logs:
        st.code("\n".join(st.session_state.logs))
    else:
        st.info("No logs yet.")

# Process control
start_button = False
if uploaded_file is not None:
    if st.session_state.processing_status["upload"]["status"] == "waiting":
        st.session_state.processing_status["upload"] = {"status": "complete", "message": f"PDF uploaded: {uploaded_file.name}"}
        log_info(f"PDF uploaded: {uploaded_file.name}")
    
    if not st.session_state.processing_started:
        start_button = st.button("Start Processing")
        if start_button:
            st.session_state.processing_started = True
            log_info("Processing started")

# Main processing function - now runs in the main Streamlit flow
if st.session_state.processing_started and not st.session_state.processing_complete:
    # Save the uploaded file
    pdf_path = save_uploaded_file(uploaded_file, st.session_state.temp_dir)
    st.session_state.output_paths["pdf"] = pdf_path
    
    # Process PDF steps sequentially with proper status updates
    
    # 1. Text extraction
    try:
        st.session_state.processing_status["text_extraction"] = {"status": "processing", "message": "Extracting text from PDF..."}
        log_info("Starting text extraction from PDF")
        extracted_text = extract_text_from_pdf(pdf_path)
        st.session_state.processing_status["text_extraction"] = {"status": "complete", "message": "Text successfully extracted"}
        log_info(f"Text extraction complete: {len(extracted_text)} characters extracted")
    except Exception as e:
        error_msg = f"Error extracting text: {str(e)}"
        log_info(error_msg)
        st.session_state.processing_status["text_extraction"] = {"status": "error", "message": error_msg}
        st.session_state.processing_complete = True
    
    # 2. Figure extraction
    if st.session_state.processing_status["text_extraction"]["status"] == "complete":
        try:
            st.session_state.processing_status["figure_extraction"] = {"status": "processing", "message": "Extracting figures from PDF..."}
            log_info("Starting figure extraction from PDF")
            
            figures_metadata_path = extract_figures(pdf_path, os.path.join(st.session_state.temp_dir, "figures"))
            st.session_state.output_paths["figures_metadata"] = figures_metadata_path
            
            # Get figure count from metadata
            import json
            with open(figures_metadata_path, 'r') as f:
                figures_data = json.load(f)
            
            st.session_state.processing_status["figure_extraction"] = {"status": "complete", "message": f"Successfully extracted {len(figures_data)} figures"}
            log_info(f"Figure extraction complete: {len(figures_data)} figures extracted")
        except Exception as e:
            error_msg = f"Error extracting figures: {str(e)}"
            log_info(error_msg)
            st.session_state.processing_status["figure_extraction"] = {"status": "error", "message": error_msg}
            st.session_state.processing_complete = True
    
    # 3. LLM processing
    if st.session_state.processing_status["figure_extraction"]["status"] == "complete":
        try:
            st.session_state.processing_status["llm_processing"] = {"status": "processing", "message": "Generating slide content with AI..."}
            log_info("Starting LLM processing for slide content generation")
            
            slides_json_path = generate_slides_content(
                extracted_text, 
                figures_metadata_path if st.session_state.output_paths["figures_metadata"] else None,
                max_slides=max_slides
            )
            st.session_state.output_paths["slides_json"] = slides_json_path
            
            # Get slide count from JSON
            with open(slides_json_path, 'r') as f:
                slides_data = json.load(f)
            
            st.session_state.processing_status["llm_processing"] = {"status": "complete", "message": f"Successfully generated content for {len(slides_data)} slides"}
            log_info(f"LLM processing complete: Generated content for {len(slides_data)} slides")
        except Exception as e:
            error_msg = f"Error generating slide content: {str(e)}"
            log_info(error_msg)
            st.session_state.processing_status["llm_processing"] = {"status": "error", "message": error_msg}
            st.session_state.processing_complete = True
    
    # 4. Markdown generation
    if st.session_state.processing_status["llm_processing"]["status"] == "complete":
        try:
            st.session_state.processing_status["markdown_generation"] = {"status": "processing", "message": "Creating Marp markdown slides..."}
            log_info("Starting markdown generation from slide content JSON")
            
            marp_md_path = convert_to_marp(slides_json_path)
            st.session_state.output_paths["marp_md"] = marp_md_path
            
            st.session_state.processing_status["markdown_generation"] = {"status": "complete", "message": "Successfully created slide deck"}
            log_info(f"Markdown generation complete: Created Marp slides at {marp_md_path}")
        except Exception as e:
            error_msg = f"Error creating markdown slides: {str(e)}"
            log_info(error_msg)
            st.session_state.processing_status["markdown_generation"] = {"status": "error", "message": error_msg}
            st.session_state.processing_complete = True
    
    # Skip remaining steps if slides_only is checked
    if slides_only and st.session_state.processing_status["markdown_generation"]["status"] == "complete":
        # Just render the slides
        try:
            st.session_state.processing_status["slide_rendering"] = {"status": "processing", "message": "Rendering slides as images..."}
            log_info("Starting slide rendering (slides-only mode)")
            
            frames_dir = render_slides(marp_md_path)
            st.session_state.output_paths["frames_dir"] = frames_dir
            
            st.session_state.processing_status["slide_rendering"] = {"status": "complete", "message": "Successfully rendered slides"}
            log_info(f"Slide rendering complete: Images saved to {frames_dir}")
        except Exception as e:
            error_msg = f"Error rendering slides: {str(e)}"
            log_info(error_msg)
            st.session_state.processing_status["slide_rendering"] = {"status": "error", "message": error_msg}
        
        log_info("Skipping audio and video generation (slides-only mode)")
        st.session_state.processing_status["audio_generation"] = {"status": "skipped", "message": "Audio generation skipped (slides only mode)"}
        st.session_state.processing_status["video_creation"] = {"status": "skipped", "message": "Video creation skipped (slides only mode)"}
        st.session_state.processing_complete = True
        log_info("Processing complete")
    
    # 5. Audio generation
    elif st.session_state.processing_status["markdown_generation"]["status"] == "complete":
        try:
            st.session_state.processing_status["audio_generation"] = {"status": "processing", "message": "Generating audio narration..."}
            log_info("Starting audio narration generation using Sarvam AI")
            
            audio_dir = generate_audio(slides_json_path)
            st.session_state.output_paths["audio_dir"] = audio_dir
            
            st.session_state.processing_status["audio_generation"] = {"status": "complete", "message": "Successfully generated audio narration"}
            log_info(f"Audio generation complete: Files saved to {audio_dir}")
        except Exception as e:
            error_msg = f"Error generating audio: {str(e)}"
            log_info(error_msg)
            st.session_state.processing_status["audio_generation"] = {"status": "error", "message": error_msg}
            st.session_state.processing_complete = True
    
    # 6. Slide rendering
    if st.session_state.processing_status["audio_generation"]["status"] == "complete":
        try:
            st.session_state.processing_status["slide_rendering"] = {"status": "processing", "message": "Rendering slides as images..."}
            log_info("Starting slide rendering using Marp CLI")
            
            frames_dir = render_slides(marp_md_path)
            st.session_state.output_paths["frames_dir"] = frames_dir
            
            st.session_state.processing_status["slide_rendering"] = {"status": "complete", "message": "Successfully rendered slides"}
            log_info(f"Slide rendering complete: Images saved to {frames_dir}")
        except Exception as e:
            error_msg = f"Error rendering slides: {str(e)}"
            log_info(error_msg)
            st.session_state.processing_status["slide_rendering"] = {"status": "error", "message": error_msg}
            st.session_state.processing_complete = True
    
    # 7. Video creation
    if st.session_state.processing_status["slide_rendering"]["status"] == "complete":
        try:
            st.session_state.processing_status["video_creation"] = {"status": "processing", "message": "Creating final video..."}
            log_info("Starting video creation using ffmpeg")
            
            video_path = create_video(frames_dir, audio_dir)
            st.session_state.output_paths["video"] = video_path
            
            st.session_state.processing_status["video_creation"] = {"status": "complete", "message": "Successfully created video"}
            log_info(f"Video creation complete: Video saved to {video_path}")
        except Exception as e:
            error_msg = f"Error creating video: {str(e)}"
            log_info(error_msg)
            st.session_state.processing_status["video_creation"] = {"status": "error", "message": error_msg}
        
        st.session_state.processing_complete = True
        log_info("Processing complete")

# Display outputs based on processing status
if st.session_state.processing_complete:
    if all(val["status"] in ["complete", "skipped"] for key, val in st.session_state.processing_status.items() if key != "upload"):
        st.success("Processing complete! 🎉")
    else:
        # Find the step that had an error
        error_steps = [key for key, val in st.session_state.processing_status.items() if val["status"] == "error"]
        if error_steps:
            st.error(f"Error in processing step: {error_steps[0]}")
            st.error(st.session_state.processing_status[error_steps[0]]["message"])
        else:
            st.warning("Processing stopped.")
    
    # Display outputs
    st.markdown("## Results")
    
    # Tabs for different outputs
    tab1, tab2, tab3, tab4 = st.tabs(["Figures", "Slides", "Audio", "Video"])
    
    with tab1:
        if st.session_state.output_paths["figures_metadata"]:
            display_figures(st.session_state.output_paths["figures_metadata"])
        else:
            st.info("No figures extracted")
    
    with tab2:
        if st.session_state.output_paths["frames_dir"]:
            display_slides_preview(st.session_state.output_paths["frames_dir"])
        else:
            st.info("No slides generated")
    
    with tab3:
        if st.session_state.output_paths["audio_dir"]:
            display_audio_preview(st.session_state.output_paths["audio_dir"])
        else:
            st.info("No audio generated")
    
    with tab4:
        if st.session_state.output_paths["video"]:
            display_video_player(st.session_state.output_paths["video"])
        else:
            st.info("No video generated")
            
    # Download options
    st.markdown("## Download Files")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.session_state.output_paths["marp_md"]:
            with open(st.session_state.output_paths["marp_md"], "r") as f:
                st.download_button(
                    label="Download Slides Markdown",
                    data=f.read(),
                    file_name="slides.md",
                    mime="text/markdown"
                )
    
    with col2:
        if st.session_state.output_paths["slides_json"]:
            with open(st.session_state.output_paths["slides_json"], "r") as f:
                st.download_button(
                    label="Download Slides JSON",
                    data=f.read(),
                    file_name="slides.json",
                    mime="application/json"
                )
    
    with col3:
        if st.session_state.output_paths["figures_metadata"]:
            with open(st.session_state.output_paths["figures_metadata"], "r") as f:
                st.download_button(
                    label="Download Figures Metadata",
                    data=f.read(),
                    file_name="figures.json",
                    mime="application/json"
                )
    
    with col4:
        if st.session_state.output_paths["video"]:
            with open(st.session_state.output_paths["video"], "rb") as f:
                st.download_button(
                    label="Download Video",
                    data=f.read(),
                    file_name="presentation.mp4",
                    mime="video/mp4"
                )
