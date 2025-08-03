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

if "text_content" not in st.session_state:
    st.session_state.text_content = ""

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

if "processing_failed" not in st.session_state:
    st.session_state.processing_failed = False

if "error_messages" not in st.session_state:
    st.session_state.error_messages = []

# Helper functions
def log_info(message):
    """Log message and update progress details"""
    logger.info(message)

def update_step_status(step_key, status, message=""):
    """Update the status of a processing step and refresh UI"""
    st.session_state.processing_status[step_key] = {
        "status": status,
        "message": message
    }


def extract_figures_with_progress(pdf_path, output_dir):
    """Extract figures with progress tracking using Mistral OCR"""
    update_step_status("figure_extraction", "processing", "Starting Mistral OCR figure extraction...")
    update_progress("figure_extraction", detail="Initializing Mistral OCR extraction")
    
    try:
        # Import the figure extractor
        from processors.figure_extractor import extract_figures
        
        update_progress("figure_extraction", detail="Processing PDF with Mistral OCR...")
        
        # Use the Mistral-based figure extractor
        figures_metadata_path = extract_figures(pdf_path, output_dir)
        
        if figures_metadata_path and os.path.exists(figures_metadata_path):
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
            
    except Exception as e:
        # Display the detailed error message from our improved Mistral extractor
        error_msg = str(e)
        
        # Make the error more readable in the UI
        if "Mistral OCR extraction failed:" in error_msg:
            # Already well formatted from our extractor
            display_error = error_msg
        else:
            # Add context for other errors
            display_error = f"Figure extraction failed: {error_msg}"
        
        update_step_status("figure_extraction", "error", "Figure extraction failed")
        update_progress("figure_extraction", detail=f"❌ {display_error}")
        
        # Store error in session state for persistent display
        error_entry = {
            "step": "Figure Extraction", 
            "error": display_error,
            "timestamp": "now"
        }
        st.session_state.error_messages.append(error_entry)
        
        # Also show the error in the main UI
        st.error(f"**Figure Extraction Error:**\n\n{display_error}")
        
        return None



def create_video_with_progress(frames_dir, audio_dir, output_path):
    """Create video with progress tracking"""
    update_step_status("video_creation", "processing", "Starting video creation...")
    update_progress("video_creation", detail="Initializing video creation...")
    
    try:
        # Count files for progress tracking
        png_files = sorted(Path(frames_dir).glob("deck.*.png"))
        audio_files = sorted(Path(audio_dir).glob("*.wav"))
        
        # audio pre-processing (1 per file) + clip creation (1 per file) + final concatenation (1)
        total_steps = len(png_files) + len(audio_files) + 1
        current_step = 0
        
        update_progress("video_creation", total=total_steps, current=current_step)
        
        # Throttled progress callback
        last_rerun_time = time.time()
        
        def progress_callback(step_name, current=None, total=None):
            nonlocal current_step, last_rerun_time
            if current is not None:
                current_step = current
            else:
                current_step += 1
            update_progress("video_creation", current=current_step, detail=step_name)
            
            # No rerun here to allow FFmpeg to finish
            pass

        video_path = create_video(frames_dir, audio_dir, output_path, progress_callback)
        st.session_state.output_paths["video"] = video_path
        
        if video_path and Path(video_path).exists():
            # Final progress update to ensure it reaches 100%
            update_progress("video_creation", current=total_steps, total=total_steps, detail="✅ Video creation completed")
            update_step_status("video_creation", "complete", "Video created successfully")
            st.rerun() # UI refresh happens only once, with the final state
            return video_path
        else:
            # The error is already logged inside create_video, just need to ensure the status is correct
            if st.session_state.processing_status["video_creation"]["status"] != 'error':
                 raise Exception("Video creation failed for an unknown reason.")
            return None
            
            
    except Exception as e:
        # Display the detailed error message from our improved ffmpeg handling
        error_msg = str(e)
        
        # Make the error more readable in the UI
        if "FFmpeg" in error_msg and "failed:" in error_msg:
            # Already well formatted from our video creator
            display_error = error_msg
        else:
            # Add context for other errors
            display_error = f"Video creation failed: {error_msg}"
        
        update_step_status("video_creation", "error", "Video creation failed")
        update_progress("video_creation", detail=f"❌ {display_error}")
        
        # Store error in session state for persistent display
        error_entry = {
            "step": "Video Creation", 
            "error": display_error,
            "timestamp": "now"
        }
        st.session_state.error_messages.append(error_entry)
        
        # Also show the error in the main UI
        st.error(f"**Video Creation Error:**\\n\\n{display_error}")
        
        # Set flag to stop further processing
        st.session_state.processing_failed = True
        
        return None

# Main UI
st.title("Paper Explainer 📑")
st.markdown("This app converts academic papers (PDFs) into concise, narrated video presentations. Upload your PDF to get started!")

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    

    
    # Processing options
    with st.expander("🔧 Processing Options", expanded=False):
        max_slides = st.number_input("Max slides", min_value=2, max_value=20, value=2)
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
    st.session_state.processing_failed = False
    st.session_state.error_messages = []  # Clear previous errors
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
    
    # Session-specific temp directory handles cleanup, so no manual cleanup is needed.
    
    # Rerun to show progress immediately
    st.rerun()

# Process the file if processing has started
if st.session_state.processing_started and not st.session_state.processing_complete:
    # Save uploaded file
    pdf_path = save_uploaded_file(uploaded_file, st.session_state.temp_dir)
    st.session_state.output_paths["pdf"] = pdf_path
    
    # Create output directories within the session's temporary directory
    session_dir = st.session_state.temp_dir
    figures_dir = os.path.join(session_dir, "figures")
    slides_dir = os.path.join(session_dir, "slides") # All slide assets in one place
    audio_dir = os.path.join(slides_dir, "audio")
    frames_dir = os.path.join(slides_dir, "frames")
    
    os.makedirs(figures_dir, exist_ok=True)
    os.makedirs(slides_dir, exist_ok=True) # Ensure the parent slides dir is created
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(frames_dir, exist_ok=True)
    
    try:
        # Step 1: Extract text
        if st.session_state.processing_status["text_extraction"]["status"] == "pending":
            update_step_status("text_extraction", "processing", "Extracting text...")
            text_content = extract_text_from_pdf(pdf_path)
            st.session_state.text_content = text_content
            update_step_status("text_extraction", "complete", f"Extracted {len(text_content)} characters")
            st.rerun()

        # Step 2: Extract figures
        if st.session_state.processing_status["figure_extraction"]["status"] == "pending":
            figures_metadata_path = extract_figures_with_progress(pdf_path, figures_dir)
            if figures_metadata_path:
                st.session_state.output_paths["figures_metadata"] = figures_metadata_path
            st.rerun()

        # Step 3: Generate slide content
        if st.session_state.processing_status["llm_processing"]["status"] == "pending":
            update_step_status("llm_processing", "processing", "Generating slide content...")
            original_filename = Path(uploaded_file.name).stem
            slides_json_path = generate_slides_content(
                st.session_state.text_content,
                st.session_state.output_paths.get("figures_metadata"),
                max_slides=max_slides,
                output_dir=slides_dir,
                original_filename=original_filename
            )
            st.session_state.output_paths["slides_json"] = slides_json_path
            update_step_status("llm_processing", "complete", "Generated slide content")
            st.rerun()

        # Step 4: Create Marp slides
        if st.session_state.processing_status["markdown_generation"]["status"] == "pending":
            update_step_status("markdown_generation", "processing", "Creating Marp slides...")
            deck_path = convert_to_marp(
                st.session_state.output_paths["slides_json"],
                st.session_state.output_paths.get("figures_metadata")
            )
            st.session_state.output_paths["deck_md"] = deck_path
            update_step_status("markdown_generation", "complete", "Created Marp slides")
            st.rerun()

        # Conditional steps for audio/video
        if not slides_only:
            # Step 5: Generate audio
            if st.session_state.processing_status["audio_generation"]["status"] == "pending":
                update_step_status("audio_generation", "processing", "Generating audio...")
                generated_audio_dir = generate_audio(st.session_state.output_paths["slides_json"], audio_dir)
                st.session_state.output_paths["audio_dir"] = generated_audio_dir
                num_files = len(os.listdir(generated_audio_dir)) if generated_audio_dir else 0
                update_step_status("audio_generation", "complete", f"Generated {num_files} audio files")
                st.rerun()

            # Step 6: Render slides to images
            if st.session_state.processing_status["slide_rendering"]["status"] == "pending":
                update_step_status("slide_rendering", "processing", "Rendering slides...")
                update_progress("slide_rendering", detail="Converting slides to PNG images")
                try:
                    rendered_frames_dir = render_slides(st.session_state.output_paths["deck_md"], frames_dir, progress_callback=update_progress_from_renderer)
                    st.session_state.output_paths["frames_dir"] = rendered_frames_dir
                    num_frames = len(os.listdir(frames_dir))
                    update_step_status("slide_rendering", "complete", f"Rendered {num_frames} slides")
                    update_progress("slide_rendering", detail=f"✅ Rendered {num_frames} slides to images")
                except Exception as e:
                    display_error = f"Slide rendering failed: {str(e)}"
                    error_entry = {
                        "step": "Slide Rendering",
                        "error": display_error,
                        "timestamp": "now"
                    }
                    st.session_state.error_messages.append(error_entry)
                    update_step_status("slide_rendering", "error", "Slide rendering failed")
                    update_progress("slide_rendering", detail=f"❌ {display_error}")
                    st.error(f"**Slide Rendering Error:**\n\n{display_error}")
                    st.session_state.processing_failed = True
                st.rerun()

            # Step 7: Create video
            if not st.session_state.processing_failed and st.session_state.processing_status["video_creation"]["status"] == "pending":
                audio_dir_path = st.session_state.output_paths.get("audio_dir")
                frames_dir_path = st.session_state.output_paths.get("frames_dir")
                if audio_dir_path and frames_dir_path:
                    video_output_path = os.path.join(slides_dir, "video.mp4")
                    video_path = create_video_with_progress(frames_dir_path, audio_dir_path, video_output_path)
                    if video_path:
                        st.session_state.output_paths["video"] = video_path
                else:
                    # If audio/slides were skipped or failed, mark video as skipped
                    update_step_status("video_creation", "skipped", "Skipped due to missing audio/slides")

        # Check if all steps are complete
        all_done = all(
            st.session_state.processing_status[s]["status"] in ("complete", "skipped")
            for s in ("text_extraction", "figure_extraction", "llm_processing",
                      "markdown_generation", "audio_generation",
                      "slide_rendering", "video_creation")
        )

        if all_done and not st.session_state.processing_complete:
            st.session_state.processing_complete = True
            
            # Clean up temp directory
            try:
                shutil.rmtree(st.session_state.temp_dir)
            except Exception as e:
                logger.warning(f"Could not clean up temp directory: {e}")
                
            # Clean up Mistral cache
            try:
                from processors.mistral_cache import clear_mistral_cache
                clear_mistral_cache()
            except ImportError:
                pass  # Cache not available

            # Final rerun to display results
            st.rerun()
    except Exception as e:
        # Clean up Mistral cache even on error
        try:
            from processors.mistral_cache import clear_mistral_cache
            clear_mistral_cache()
        except ImportError:
            pass
        
        st.error(f"Processing failed: {str(e)}")
        logger.error(f"Processing failed: {str(e)}")

# Display results
if st.session_state.processing_complete:
    st.markdown("---")
    
    # Show errors prominently if any occurred
    if st.session_state.error_messages:
        st.markdown("## ❌ Processing Errors")
        st.error("**Some steps failed during processing. See details below:**")
        
        for error in st.session_state.error_messages:
            with st.expander(f"❌ {error['step']} Error", expanded=True):
                st.code(error['error'], language=None)
        
        st.markdown("---")
    
    # Results section
    if st.session_state.error_messages:
        st.markdown("## 📋 Partial Results")
        st.info("Some processing steps completed successfully before the error occurred.")
    else:
        st.markdown("## 🎉 Results")
    
    # Create tabs for different outputs  
    if st.session_state.error_messages:
        video_tab, slides_tab, figures_tab, debug_tab = st.tabs(["🎬 Video", "📋 Slides", "🖼️ Figures", "🐛 Debug"])
    else:
        video_tab, slides_tab, figures_tab = st.tabs(["🎬 Video", "📋 Slides", "🖼️ Figures"])
        debug_tab = None

    with video_tab:
        if st.session_state.output_paths.get("video"):
            display_video_player(st.session_state.output_paths["video"])
        else:
            st.info("Video was not generated or is unavailable.")

    with slides_tab:
        if st.session_state.output_paths.get("frames_dir"):
            display_slides_preview(st.session_state.output_paths["frames_dir"])
        else:
            st.info("Slides were not generated or are unavailable.")

    with figures_tab:
        if st.session_state.output_paths.get("figures_metadata"):
            display_figures(st.session_state.output_paths["figures_metadata"])
        else:
            st.info("No figures were extracted or they are unavailable.")
    
    # Debug tab (only shown when there are errors)
    if debug_tab is not None:
        with debug_tab:
            st.markdown("### 🐛 Debug Information")
            
            st.markdown("**Processing Status:**")
            for step, status in st.session_state.processing_status.items():
                status_icon = "✅" if status["status"] == "complete" else "❌" if status["status"] == "error" else "⏳"
                st.write(f"{status_icon} {step.replace('_', ' ').title()}: {status['status']} - {status.get('message', '')}")
            
            st.markdown("**Session State:**")
            debug_info = {
                "processing_started": st.session_state.processing_started,
                "processing_complete": st.session_state.processing_complete, 
                "processing_failed": st.session_state.processing_failed,
                "error_count": len(st.session_state.error_messages),
                "output_paths": list(st.session_state.output_paths.keys()) if hasattr(st.session_state, 'output_paths') else []
            }
            st.json(debug_info)
            
            if st.session_state.error_messages:
                st.markdown("**Full Error Details:**")
                for i, error in enumerate(st.session_state.error_messages):
                    st.markdown(f"**Error {i+1}: {error['step']}**")
                    st.code(error['error'], language=None)

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit • [GitHub](https://github.com/your-repo)")
