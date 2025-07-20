"""Temporary copy of ui_components with Streamlit deprecation fix.
This file is identical to utils/ui_components.py but replaces the
deprecated `use_column_width` argument with `use_container_width`.
After validation we can merge changes back into the main file.
"""
import os
import json
from pathlib import Path
import streamlit as st

# --- Original helper functions (unchanged except deprecation fix) ---

def display_figures(figures_metadata_path):
    """Display extracted figures in a grid layout."""
    try:
        with open(figures_metadata_path, 'r') as f:
            figures_data = json.load(f)
        if not figures_data:
            st.info("No figures extracted from the PDF.")
            return
        st.markdown(f"### {len(figures_data)} Figures Extracted")
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
    """Display slide previews in the UI."""
    try:
        frames_path = Path(frames_dir)
        png_files = sorted(frames_path.glob("deck.*.png"))
        if not png_files:
            st.info("No slide images available for preview.")
            return
        st.markdown(f"### {len(png_files)} Slides Generated")
        selected_slide = st.slider("Browse slides", 1, len(png_files), 1)
        st.image(png_files[selected_slide-1], use_container_width=True)
        if st.checkbox("Show all slides"):
            cols = st.columns(min(3, len(png_files)))
            for i, png_file in enumerate(png_files):
                col_idx = i % len(cols)
                with cols[col_idx]:
                    st.image(png_file, caption=f"Slide {i+1}", use_container_width=True)
    except Exception as e:
        st.error(f"Error displaying slide previews: {str(e)}")


def display_audio_preview(audio_dir):
    """Display audio previews in the UI."""
    try:
        audio_path = Path(audio_dir)
        audio_files = sorted(audio_path.glob("*.wav"))
        if not audio_files:
            st.info("No audio files available for preview.")
            return
        st.markdown(f"### {len(audio_files)} Audio Tracks")
        for audio_file in audio_files:
            st.audio(str(audio_file))
    except Exception as e:
        st.error(f"Error displaying audio previews: {str(e)}")
