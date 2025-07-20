#!/usr/bin/env python3
"""
Test script to verify the compact UI components work correctly
"""

import streamlit as st
import sys
import os

# Add the project root to the path so we can import our modules
sys.path.append(os.path.abspath('.'))

from utils.ui_components import display_compact_progress_step

def main():
    st.title("Compact UI Test")
    
    st.markdown("### Testing Compact Progress Steps")
    
    # Test different statuses
    display_compact_progress_step("Upload PDF", "complete", message="test.pdf uploaded")
    display_compact_progress_step("Extract Text", "complete", message="5,234 characters extracted")
    display_compact_progress_step("Extract Figures", "processing", current=2, total=4, message="Analyzing page 2...")
    display_compact_progress_step("Generate Content", "waiting")
    display_compact_progress_step("Create Slides", "waiting")
    display_compact_progress_step("Generate Audio", "waiting")
    display_compact_progress_step("Render Images", "waiting")
    display_compact_progress_step("Create Video", "waiting")
    
    st.markdown("---")
    st.markdown("### Error Example")
    display_compact_progress_step("Extract Figures", "error", message="API key not found")

if __name__ == "__main__":
    main()
