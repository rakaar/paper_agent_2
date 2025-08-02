"""
Mistral OCR Configuration for Paper Explainer
"""

import os

# API Keys - Always use environment variables for security
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Feature flags
ENABLE_ENHANCED_FIGURE_CONTEXT = True  # Use enhanced figure-text relationship extraction
CLEANUP_TEMP_FILES = True             # Clean up temporary Mistral output files

# Processing limits (to conserve API credits during testing)
MAX_PAGES_FOR_TESTING = None  # Set to a number to limit pages, or None for all pages

# Output settings
FIGURE_IMAGE_FORMAT = "png"    # Format for extracted figure images
FIGURE_DPI = 300              # DPI for figure extraction