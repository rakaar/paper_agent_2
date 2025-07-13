import streamlit as st
import os
import json
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
                    st.image(png_path, caption=title, use_column_width=True)
                    with st.expander("Caption"):
                        st.write(caption)
                else:
                    st.error(f"Figure file not found: {png_path}")
    
    except Exception as e:
        st.error(f"Error displaying figures: {str(e)}")

def display_slides_preview(frames_dir):
    """
    Display slide previews in the UI
    
    Args:
        frames_dir (str): Path to the directory containing slide PNG frames
    """
    try:
        frames_path = Path(frames_dir)
        png_files = sorted(frames_path.glob("deck.*.png"))
        
        if not png_files:
            st.info("No slide images available for preview.")
            return
        
        st.markdown(f"### {len(png_files)} Slides Generated")
        
        # Create a slider to browse through slides
        selected_slide = st.slider("Browse slides", 1, len(png_files), 1)
        
        # Display the selected slide
        st.image(png_files[selected_slide-1], use_column_width=True)
        
        # Option to view all slides
        if st.checkbox("Show all slides"):
            # Display slides in a grid (up to 3 columns)
            cols = st.columns(min(3, len(png_files)))
            
            for i, png_file in enumerate(png_files):
                col_idx = i % len(cols)
                with cols[col_idx]:
                    st.image(png_file, caption=f"Slide {i+1}", use_column_width=True)
    
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
