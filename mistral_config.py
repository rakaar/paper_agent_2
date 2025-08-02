"""
Mistral OCR Configuration for Paper Explainer
"""

import os

# API Keys - Always use environment variables for security
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Validate API key configuration
def validate_mistral_config():
    """Validate Mistral configuration and provide helpful error messages"""
    if not MISTRAL_API_KEY:
        raise ValueError(
            "MISTRAL_API_KEY environment variable is not set.\n"
            "Please set it with one of these methods:\n"
            "  1. Export in terminal: export MISTRAL_API_KEY='your-api-key'\n"
            "  2. Add to .env file: MISTRAL_API_KEY=your-api-key\n"
            "  3. Set in your shell profile (~/.bashrc, ~/.zshrc)\n"
            "\nGet your API key from: https://console.mistral.ai"
        )
    
    if not MISTRAL_API_KEY.startswith("sk-live-") and not MISTRAL_API_KEY.startswith("kq"):
        print(f"Warning: API key format looks unusual. Expected format: sk-live-... or similar")
    
    return True

# Feature flags
ENABLE_ENHANCED_FIGURE_CONTEXT = True  # Use enhanced figure-text relationship extraction
CLEANUP_TEMP_FILES = True             # Clean up temporary Mistral output files

# Processing limits (to conserve API credits during testing)
MAX_PAGES_FOR_TESTING = None  # Set to a number to limit pages, or None for all pages

# Output settings
FIGURE_IMAGE_FORMAT = "png"    # Format for extracted figure images
FIGURE_DPI = 300              # DPI for figure extraction

# Debug settings
DEBUG_MISTRAL_CALLS = True     # Print debug information for Mistral API calls