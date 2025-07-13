import os
import streamlit as st
import tempfile
import time
from pathlib import Path

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

# Process control
start_button = None
if uploaded_file is not None:
    if st.session_state.processing_status["upload"]["status"] == "waiting":
        st.session_state.processing_status["upload"] = {"status": "complete", "message": f"PDF uploaded: {uploaded_file.name}"}
    
    if all(val["status"] != "processing" for val in st.session_state.processing_status.values()):
        start_button = st.button("Start Processing")

# Main processing function
def process_pdf(pdf_path):
    # 1. Text extraction
    try:
        st.session_state.processing_status["text_extraction"] = {"status": "processing", "message": "Extracting text from PDF..."}
        # No rerun needed in synchronous flow
        
        extracted_text = extract_text_from_pdf(pdf_path)
        st.session_state.processing_status["text_extraction"] = {"status": "complete", "message": "Text successfully extracted"}
    except Exception as e:
        st.session_state.processing_status["text_extraction"] = {"status": "error", "message": f"Error extracting text: {str(e)}"}
        st.experimental_rerun()
        return
    
    # 2. Figure extraction
    try:
        st.session_state.processing_status["figure_extraction"] = {"status": "processing", "message": "Extracting figures from PDF..."}
        st.experimental_rerun()
        
        figures_metadata_path = extract_figures(pdf_path, os.path.join(st.session_state.temp_dir, "figures"))
        st.session_state.output_paths["figures_metadata"] = figures_metadata_path
        
        # Get figure count from metadata
        import json
        with open(figures_metadata_path, 'r') as f:
            figures_data = json.load(f)
        
        st.session_state.processing_status["figure_extraction"] = {"status": "complete", "message": f"Successfully extracted {len(figures_data)} figures"}
    except Exception as e:
        st.session_state.processing_status["figure_extraction"] = {"status": "error", "message": f"Error extracting figures: {str(e)}"}
        st.experimental_rerun()
        return
    
    # 3. LLM processing
    try:
        st.session_state.processing_status["llm_processing"] = {"status": "processing", "message": "Generating slide content with AI..."}
        st.experimental_rerun()
        
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
    except Exception as e:
        st.session_state.processing_status["llm_processing"] = {"status": "error", "message": f"Error generating slide content: {str(e)}"}
        st.experimental_rerun()
        return
    
    # 4. Markdown generation
    try:
        st.session_state.processing_status["markdown_generation"] = {"status": "processing", "message": "Creating Marp markdown slides..."}
        st.experimental_rerun()
        
        marp_md_path = convert_to_marp(slides_json_path)
        st.session_state.output_paths["marp_md"] = marp_md_path
        
        st.session_state.processing_status["markdown_generation"] = {"status": "complete", "message": "Successfully created slide deck"}
    except Exception as e:
        st.session_state.processing_status["markdown_generation"] = {"status": "error", "message": f"Error creating markdown slides: {str(e)}"}
        st.experimental_rerun()
        return
    
    # Skip remaining steps if slides_only is checked
    if slides_only:
        # Just render the slides
        try:
            st.session_state.processing_status["slide_rendering"] = {"status": "processing", "message": "Rendering slides as images..."}
            st.experimental_rerun()
            
            frames_dir = render_slides(marp_md_path)
            st.session_state.output_paths["frames_dir"] = frames_dir
            
            st.session_state.processing_status["slide_rendering"] = {"status": "complete", "message": "Successfully rendered slides"}
        except Exception as e:
            st.session_state.processing_status["slide_rendering"] = {"status": "error", "message": f"Error rendering slides: {str(e)}"}
        
        st.session_state.processing_status["audio_generation"] = {"status": "skipped", "message": "Audio generation skipped (slides only mode)"}
        st.session_state.processing_status["video_creation"] = {"status": "skipped", "message": "Video creation skipped (slides only mode)"}
        st.experimental_rerun()
        return
    
    # 5. Audio generation
    try:
        st.session_state.processing_status["audio_generation"] = {"status": "processing", "message": "Generating audio narration..."}
        st.experimental_rerun()
        
        audio_dir = generate_audio(slides_json_path)
        st.session_state.output_paths["audio_dir"] = audio_dir
        
        st.session_state.processing_status["audio_generation"] = {"status": "complete", "message": "Successfully generated audio narration"}
    except Exception as e:
        st.session_state.processing_status["audio_generation"] = {"status": "error", "message": f"Error generating audio: {str(e)}"}
        st.experimental_rerun()
        return
    
    # 6. Slide rendering
    try:
        st.session_state.processing_status["slide_rendering"] = {"status": "processing", "message": "Rendering slides as images..."}
        st.experimental_rerun()
        
        frames_dir = render_slides(marp_md_path)
        st.session_state.output_paths["frames_dir"] = frames_dir
        
        st.session_state.processing_status["slide_rendering"] = {"status": "complete", "message": "Successfully rendered slides"}
    except Exception as e:
        st.session_state.processing_status["slide_rendering"] = {"status": "error", "message": f"Error rendering slides: {str(e)}"}
        st.experimental_rerun()
        return
    
    # 7. Video creation
    try:
        st.session_state.processing_status["video_creation"] = {"status": "processing", "message": "Creating final video..."}
        st.experimental_rerun()
        
        video_path = create_video(frames_dir, audio_dir)
        st.session_state.output_paths["video"] = video_path
        
        st.session_state.processing_status["video_creation"] = {"status": "complete", "message": "Successfully created video"}
    except Exception as e:
        st.session_state.processing_status["video_creation"] = {"status": "error", "message": f"Error creating video: {str(e)}"}
    
    st.experimental_rerun()

# Start processing if button is clicked
if start_button:
    # Save the uploaded file
    pdf_path = save_uploaded_file(uploaded_file, st.session_state.temp_dir)
    st.session_state.output_paths["pdf"] = pdf_path
    
    # Process directly without threading
    process_pdf(pdf_path)

# Display outputs based on processing status
if all(val["status"] == "complete" for key, val in st.session_state.processing_status.items() if key != "upload"):
    st.success("Processing complete! 🎉")
    
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
                    file_name="slides_data.json",
                    mime="application/json"
                )
    
    with col3:
        if st.session_state.output_paths["figures_metadata"]:
            with open(st.session_state.output_paths["figures_metadata"], "r") as f:
                st.download_button(
                    label="Download Figures Metadata",
                    data=f.read(),
                    file_name="figures_metadata.json",
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

# Footer
st.markdown("---")
st.markdown("Paper Explainer - Convert academic papers to video presentations")
