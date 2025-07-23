import streamlit as st
import os
import json
import time
from pathlib import Path

def step_header(title, status):
    """
    Display a step header with status indicator
    
    Args:
        title (str): Step title
        status (str): Status (waiting, processing, complete, error, skipped, pending)
    """
    status_icons = {
        "waiting": "⏱️",
        "processing": "🔄",
        "complete": "✅",
        "error": "❌",
        "skipped": "⏭️",
        "pending": "⏳"
    }
    
    icon = status_icons.get(status, "❓")
    
    if status == "processing":
        st.markdown(f"### {icon} {title}")
        st.spinner("Processing...")
    else:
        st.markdown(f"### {icon} {title}")

def processing_status(step_name):
    """
    Get the current processing status for a step
    
    Args:
        step_name (str): Name of the step in session state
    
    Returns:
        dict: Status info for the step
    """
    return st.session_state.processing_status.get(step_name, {"status": "pending", "message": ""})

def display_figures(figures_metadata_path):
    """
    Display extracted figures in the UI
    
    Args:
        figures_metadata_path (str): Path to the figures metadata JSON file
    """
    try:
        with open(figures_metadata_path, 'r') as f:
            figures_data = json.load(f)
        
        if not figures_data:
            st.info("No figures extracted from the PDF.")
            return
        
        st.markdown(f"### {len(figures_data)} Figures Extracted")
        
        # Display figures in a grid (up to 3 columns)
        cols = st.columns(min(3, len(figures_data)))
        
        for i, figure in enumerate(figures_data):
            col_idx = i % len(cols)
            with cols[col_idx]:
                title = figure.get('title', f'Figure {i+1}')
                caption = figure.get('caption', 'No caption available.')
                png_path = figure.get('markdown_path', '')
                
                if os.path.exists(png_path):
                    st.image(png_path, caption=title, use_container_width=True)
                    with st.expander("Caption"):
                        st.write(caption)
                else:
                    st.error(f"Figure file not found: {png_path}")
    
    except Exception as e:
        st.error(f"Error displaying figures: {str(e)}")

def display_slides_preview(frames_dir):
    """
    Display slide previews in the UI with a carousel-style interface.

    Args:
        frames_dir (str): Path to the directory containing slide PNG frames.
    """
    try:
        frames_path = Path(frames_dir)
        png_files = sorted(frames_path.glob("deck.*.png"))

        if not png_files:
            st.info("No slide images available for preview.")
            return

        st.markdown(f"### {len(png_files)} Slides Generated")

        # Initialize session state for slide index
        if 'slide_index' not in st.session_state:
            st.session_state.slide_index = 0

        # Ensure index is within bounds
        num_slides = len(png_files)
        st.session_state.slide_index = max(0, min(st.session_state.slide_index, num_slides - 1))

        # Create columns for navigation
        col1, col2, col3 = st.columns([1, 10, 1])

        with col1:
            if st.button("◀️ Prev", use_container_width=True):
                if st.session_state.slide_index > 0:
                    st.session_state.slide_index -= 1
                    st.rerun()

        with col3:
            if st.button("Next ▶️", use_container_width=True):
                if st.session_state.slide_index < num_slides - 1:
                    st.session_state.slide_index += 1
                    st.rerun()
        
        # Display the current slide
        current_slide_index = st.session_state.slide_index
        st.image(
            str(png_files[current_slide_index]),
            caption=f"Slide {current_slide_index + 1}/{num_slides}",
            use_container_width=True
        )

        # Option to view all slides
        if st.checkbox("Show all slides"):
            cols = st.columns(min(3, num_slides))
            for i, png_file in enumerate(png_files):
                with cols[i % len(cols)]:
                    st.image(str(png_file), caption=f"Slide {i + 1}", use_container_width=True)

    except Exception as e:
        st.error(f"Error displaying slide previews: {str(e)}")

def display_audio_preview(audio_dir):
    """
    Display audio previews in the UI
    
    Args:
        audio_dir (str): Path to the directory containing audio files
    """
    try:
        audio_path = Path(audio_dir)
        audio_files = sorted(audio_path.glob("*.wav"))
        
        if not audio_files:
            st.info("No audio files available for preview.")
            return
        
        st.markdown(f"### {len(audio_files)} Audio Narrations Generated")
        
        # Create a selectbox to choose which audio to play
        audio_options = [f"Slide {i+1}" for i in range(len(audio_files))]
        selected_audio = st.selectbox("Select audio to play", audio_options)
        
        # Get the index of the selected audio
        selected_idx = audio_options.index(selected_audio)
        
        # Display audio player for the selected audio
        st.audio(audio_files[selected_idx])
        
    except Exception as e:
        st.error(f"Error displaying audio previews: {str(e)}")

def display_video_player(video_path):
    """
    Display video player in the UI
    
    Args:
        video_path (str): Path to the generated video file
    """
    try:
        if not os.path.exists(video_path):
            st.info("No video available for preview.")
            return
        
        st.markdown("### Final Video Presentation")
        
        # Display video player
        st.video(video_path)
        
    except Exception as e:
        st.error(f"Error displaying video player: {str(e)}")

def display_compact_progress_step(step_name, status, current=None, total=None, message=""):
    """
    Display a compact progress step as a bullet point with emoji indicators
    
    Args:
        step_name (str): Name of the step
        status (str): Status (waiting, processing, complete, error, skipped)
        current (int, optional): Current progress count
        total (int, optional): Total items to process
        message (str): Additional message to display
    """
    status_config = {
        "waiting": {"icon": "⏳", "color": "#666666"},
        "processing": {"icon": "🔄", "color": "#1f77b4"},
        "complete": {"icon": "✅", "color": "#2ca02c"},
        "error": {"icon": "❌", "color": "#d62728"},
        "skipped": {"icon": "⏭️", "color": "#ff7f0e"}
    }
    
    config = status_config.get(status, {"icon": "❓", "color": "#666666"})
    
    # Build progress text
    progress_text = ""
    if current is not None and total is not None and total > 0:
        progress_text = f" ({current}/{total})"
    
    # Build message text
    message_text = f" - {message}" if message else ""
    
    # Create the bullet point
    bullet_text = f"**{config['icon']} {step_name}**{progress_text}{message_text}"
    
    # Display with appropriate color
    if status == "processing":
        st.markdown(f":blue[{bullet_text}]")
    elif status == "complete":
        st.markdown(f":green[{bullet_text}]")
    elif status == "error":
        st.markdown(f":red[{bullet_text}]")
    else:
        st.markdown(bullet_text)

def display_live_progress():
    """
    Display live progress for all processing steps in a compact format
    """
    if "progress_details" not in st.session_state:
        st.session_state.progress_details = {}
    
    # Define the processing steps in order
    steps = [
        {"key": "upload", "name": "Upload PDF"},
        {"key": "text_extraction", "name": "Extract Text"},
        {"key": "figure_extraction", "name": "Extract Figures"},
        {"key": "llm_processing", "name": "Generate Content"},
        {"key": "markdown_generation", "name": "Create Slides"},
        {"key": "audio_generation", "name": "Generate Audio"},
        {"key": "slide_rendering", "name": "Render Images"},
        {"key": "video_creation", "name": "Create Video"}
    ]
    
    st.markdown("### 🔄 Processing Status")
    
    # Show current active step with spinner
    current_step = None
    for step in steps:
        step_key = step["key"]
        step_status = st.session_state.processing_status.get(step_key, {"status": "waiting", "message": ""})
        if step_status["status"] == "processing":
            current_step = step["name"]
            break
    
    if current_step:
        with st.spinner(f"Processing: {current_step}..."):
            st.empty()  # Just show the spinner
    
    # Show compact progress list
    for step in steps:
        step_key = step["key"]
        step_status = st.session_state.processing_status.get(step_key, {"status": "waiting", "message": ""})
        progress_info = st.session_state.progress_details.get(step_key, {})
        
        display_compact_progress_step(
            step_name=step["name"],
            status=step_status["status"],
            current=progress_info.get("current"),
            total=progress_info.get("total"),
            message=step_status.get("message", "")
        )

def update_progress(step_key, current=None, total=None, detail=None):
    """
    Update progress information for a step
    
    Args:
        step_key (str): The step key (e.g., 'figure_extraction')
        current (int, optional): Current progress count
        total (int, optional): Total items to process
        detail (str, optional): Detail message to add
    """
    if "progress_details" not in st.session_state:
        st.session_state.progress_details = {}
    
    if step_key not in st.session_state.progress_details:
        st.session_state.progress_details[step_key] = {
            "current": 0,
            "total": 0,
            "details": []
        }
    
    progress_info = st.session_state.progress_details[step_key]
    
    if current is not None:
        progress_info["current"] = current
    if total is not None:
        progress_info["total"] = total
    if detail is not None:
        timestamp = time.strftime("%H:%M:%S")
        progress_info["details"].append(f"[{timestamp}] {detail}")
        # Keep only last 20 details
        if len(progress_info["details"]) > 20:
            progress_info["details"] = progress_info["details"][-20:]

    # Echo progress to terminal for visibility
    if detail is not None:
        print(detail)
    # Avoid st.rerun() here; frequent reruns abort the long callback and desync UI
