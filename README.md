# Paper Explainer

Convert any academic paper into a short, narrated slide-deck video – end-to-end, in one click.

Key capabilities (2025-07):
* 📑 PDF text extraction
* 🖼️ Figure detection & cropping (vision LLM)
* ✨ Gemini-pro slide synthesis with Markdown + narration script
* 🔊 Sarvam AI TTS per-slide narration
* 🖼️→🎞️ Marp-CLI rendering to PNG frames
* 🎬 ffmpeg assembly into MP4
* 🌐 Streamlit UI with live step-by-step progress (⏳ → 🔄 → ✅)
* Flexible slide count (2-20) and *slides-only* fast-mode

---


1. ~~communication with LLM about figures and location is messed up. Handle that~~
 - ~~first see where and how figures are stored~~
 - ~~modify prompt to include figures whenever relevant~~

2. ~~Format text to LLM for creating slides.~~

3. ~~Improve deck creation by more detailed prompt~~

4. ~~issue in making slides now.~~ ✅ **FIXED** - JSON file creation and Marp conversion

5. tests to test without UI

6. merge in the main branch

7. Improve figure cropping 

8. get sub figure cropping

9. more customization on methods?

10. ollama gemma-3n on server

## Recent Fixes & Improvements (2025-01)

✅ **Fixed JSON File Creation Bug**: Resolved issue where slides JSON files were being created then immediately deleted due to conflicting cleanup mechanisms

✅ **Improved File Naming**: Restored consistent filename convention (`<original_filename>_slides_plan.json`) instead of hash-based naming

✅ **Enhanced Error Handling**: Better error messages and debugging for `json2marp.py` conversion process

✅ **Streamlit UI Enhancements**: Added comprehensive progress tracking with real-time status updates and emoji indicators

✅ **Fixed Missing Import**: Resolved `sys` import issue in `json2marp.py` that was causing script failures

## Directory Layout

```
paper-explainer/
│
├─ figures/                # Auto-generated figures from the PDF
│   ├─ figure-1.png        # Example extracted figure
│   └─ figures_metadata.json # JSON file with figure captions and paths
│
├─ slides/                 # All auto-generated presentation artifacts
│   ├─ deck.md             # Marp Markdown (source of truth for slides)
│   ├─ frames/             # PNG images of each slide (e.g., deck.001.png)
│   ├─ audio/              # WAV audio files for each slide's narration
│   ├─ <original_filename>_slides_plan.json # Structured JSON output from LLM
│   └─ video.mp4           # Final generated video
│
├─ pdf2json.py             # Helper module for interacting with the Gemini LLM.
├─ json2marp.py            # Converts the slide plan JSON into Marp Markdown format.
├─ txt2slides.py           # Main script: orchestrates the entire text-to-video pipeline.
├─ extract_images_llm.py   # Extracts figures and captions from a PDF using a multimodal LLM.
└─ requirements.txt        # Python package dependencies.
```

## Usage

### 🌐 **Streamlit Web Interface (Recommended)**

The easiest way to use Paper Explainer is through the enhanced Streamlit web interface with live progress tracking:

```bash
# Activate virtual environment
source venv/bin/activate

# Start the web interface
streamlit run streamlit_app_enhanced.py --server.port 8502
```

Then open your browser to `http://localhost:8502` and:
1. Upload your PDF file
2. Choose slide count (2-20)
3. Watch real-time progress as your video is created!

### 📝 **Command Line Interface**

For advanced users, you can also use the command-line interface. The process is a two-step pipeline to ensure figures are included correctly.

**Step 1: Extract Figures from the PDF**

This script analyzes the PDF, extracts all figures, and saves them along with a metadata file. This step is optional but required if you want to embed figures from the paper into the video.

```bash
python3 extract_images_llm.py path/to/your/paper.pdf --output_dir figures
```
This command creates a `figures/` directory containing the extracted figure images and a `figures_metadata.json` file.

**Step 2: Generate the Video Presentation**

This is the main script that generates the video. If you completed Step 1, provide the path to the figure metadata to embed the images in your presentation.

*   **To generate a video with figures:**
    ```bash
    python3 txt2slides.py path/to/your/paper.pdf --figures-path figures/figures_metadata.json
    ```

*   **To generate a video without figures:**
    ```bash
    python3 txt2slides.py path/to/your/paper.pdf
    ```

The script will perform all subsequent steps, and the final video will be available at `slides/video.mp4`.

## Core Components & What They Do

*   **`pdf2json.py`**: This file contains the `call_llm` helper function, which is responsible for sending prompts to the Gemini 2.5 Pro LLM and returning its raw JSON response. It handles authentication, retries, and model selection internally.

*   **`json2marp.py`**: This script takes the structured JSON output from the LLM (generated by `txt2slides.py`) and converts it into Marp Markdown format. Marp Markdown is a specialized Markdown syntax for creating slide decks, with built-in support for MathJax for rendering mathematical equations.

*   **Whitespace-compaction in `txt2slides.py`**: The script now automatically collapses unnecessary internal spaces, tabs, and blank lines in the prompts before sending them to Gemini. This reduces token usage while retaining readability. For debugging, the raw *and* compacted prompts are written to `slides/full_llm_prompt.txt` (which remains git-ignored by default).

*   **`extract_images_llm.py`**: Implements a sophisticated, vision-based pipeline to extract figures from PDF documents. It works by converting each PDF page into a high-resolution image and sending it to a multimodal LLM (Gemini 2.5 Pro). The LLM is prompted not only to find the precise bounding box of each figure but also to extract its title (e.g., "Figure 1") and full caption text.

    **Output:** For each figure found, the script generates two files in a dedicated output directory (e.g., `extracted_figures_llm_<pdf_name>/`):
    1.  An image file (e.g., `figure-1.png`) cropped directly from the PDF.
    2.  A JSON metadata file (e.g., `figure-1.json`) containing the `figure_id`, `page_num`, `title`, `caption`, and the corresponding `png_filename`.
    
    This structured output makes the extracted figures easy to use in downstream tasks. The script also includes robust error handling, including retries with exponential backoff for API rate limits and resilient JSON parsing.

    **Usage:** The script is run from the command line, with the path to the PDF as a required argument.

    ```bash
    # Activate your virtual environment
    source venv/bin/activate

    # Run on a specific PDF, saving to the default output directory
    python3 extract_images_llm.py path/to/your/document.pdf

    # Process only the first 5 pages and specify a custom output directory
    python3 extract_images_llm.py path/to/your/document.pdf --max_pages 5 --output_dir my_extracted_figures
    ```

*   **`txt2slides.py`**: This is the main orchestration script for the entire pipeline. It performs the following steps:
    1.  Accepts either plain-text (`.txt`) or PDF (`.pdf`) files as input. For PDFs, it extracts the raw text content.
    2.  If the input is a PDF, it calls `extract_images_llm.py` to identify and save all figures from the document.
    3.  Constructs a prompt for the Gemini LLM, instructing it to break the text into a specified number of slides with concise content and detailed audio narration.
    4.  Calls `pdf2json.py` to interact with the LLM and get the structured slide data.
    5.  Saves the raw LLM output as a JSON file (`slides/<original_filename>_slides_plan.json`).
    6.  Calls `json2marp.py` to convert the LLM's JSON into a Marp Markdown file (`slides/deck.md`), potentially embedding the paths to the extracted figures.
    6.  Generates audio narration files (`slides/audio/slideXX.wav`) for each slide using Sarvam AI's Text-to-Speech (TTS) service.
    7.  Renders the Marp Markdown file into individual PNG image frames (`slides/frames/deck.00X.png`) using the `marp-cli` tool.
    8.  Combines the generated PNG frames and audio files into a single MP4 video (`slides/video.mp4`) using `ffmpeg`.

*   **`debug_video.py`**: A standalone utility script for debugging the video creation step. It regenerates the `video.mp4` file from the existing PNG frames in `slides/frames/` and WAV audio files in `slides/audio/`. This is useful for testing changes to the video encoding without re-running the entire LLM and TTS pipeline.

*   **`requirements.txt`**: Lists all Python libraries required for this project. These can be installed using `pip`.

*   **`.gitignore`**: Configured to ignore temporary files, virtual environments, and all generated output files, ensuring a clean Git repository.

## Setup

To set up and run this project, you'll need Python, Node.js (for `marp-cli`), and `ffmpeg` installed on your system.

### 1. Clone the Repository

```bash
git clone <repository_url>
cd paper-explainer
```

### 2. Python Environment Setup

It's highly recommended to use a virtual environment to manage Python dependencies.

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Install Node.js and Marp CLI

`marp-cli` is a Node.js package that converts Marp Markdown to various formats, including PNGs. It requires Node.js (version 18 or higher is recommended).

```bash
# Install Node.js (if not already installed) - refer to Node.js official documentation for your OS
# Example for Ubuntu:
# sudo apt update
# sudo apt install nodejs npm

# Install marp-cli globally
npm i -g @marp-team/marp-cli
```

### 4. Install FFmpeg

FFmpeg is a powerful command-line tool used for handling multimedia files. It's essential for combining the image frames and audio into a video.

```bash
# On Debian/Ubuntu:
sudo apt update
sudo apt install ffmpeg

# On Fedora:
sudo dnf install ffmpeg

# On Arch Linux:
sudo pacman -S ffmpeg

# For other operating systems, refer to the official FFmpeg website or your system's documentation.
```

### 5. Set API Keys

This project uses API keys for Gemini (via `pdf2json.py`) and Sarvam AI (for TTS). **Never hardcode your API keys in the source code.** Instead, set them as environment variables.

*   **`GEMINI_API_KEY`**: Your API key for Google Gemini.
*   **`SARVAM_API_KEY`**: Your API key for Sarvam AI.

**Example (Linux/macOS):**

```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
export SARVAM_API_KEY="YOUR_SARVAM_API_KEY"
```

**Example (Windows Command Prompt):**

```cmd
set GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
set SARVAM_API_KEY="YOUR_SARVAM_API_KEY"
```

For persistent environment variables, refer to your operating system's documentation.

## Usage

To run the pipeline, execute the `txt2slides.py` script with one or more plain-text (`.txt`) files as arguments.

```bash
source venv/bin/activate # Activate your virtual environment
python3 txt2slides.py paper_structured_page_1.txt paper_structured_page_2.txt
```

### What You Get

After successful execution, the `slides/` directory will contain:

*   **`deck.md`**: The Marp Markdown file generated from the LLM's output.
*   **`frames/`**: A directory containing PNG images of each slide (e.g., `deck.001.png`, `deck.002.png`).
*   **`audio/`**: A directory containing WAV audio files for each slide's narration (e.g., `slide01.wav`, `slide02.wav`).
*   **`<original_filename>_slides_plan.json`**: A JSON file containing the structured data for each slide (title, content, audio script) as returned by the LLM.

*   **`video.mp4`**: The final MP4 video presentation, combining the slide images and their respective audio narrations.

## Command-line Flags

* `--max-slides N` – force the LLM to generate exactly N slides, overriding the automatic heuristic.
* `--slides-only` – skip audio narration and video assembly; still renders PNG frames for a fast visual check.

Example rapid-iteration run:

```bash
python3 txt2slides.py path/to/paper.pdf \
    --figures-path extracted_figures_llm/figures_metadata.json \
    --max-slides 12 --slides-only
```

---

## UI Components

The project includes a Streamlit web interface for interactive usage and step-by-step visualization of the pipeline. The UI components are organized as follows:

### Main App File

* **`streamlit_app.py`**: Main Streamlit app providing a web interface for the paper-to-video pipeline. Offers file upload, processing status tracking, and downloadable outputs.
* **`streamlit_app_enhanced.py`**: Enhanced version with live progress tracking, improved logging and error handling.

### Processor Modules

The `processors/` directory contains modular components for each step of the pipeline:

* **`text_extractor.py`**: Extracts text from PDF documents using PyMuPDF.
* **`figure_extractor.py`**: Handles figure extraction by calling the existing `extract_images_llm.py` script.
* **`llm_processor.py`**: Generates slide content by interfacing with Gemini LLM.
* **`marp_converter.py`**: Converts JSON slide content to Marp Markdown using `json2marp.py`.
* **`audio_generator.py`**: Creates audio narration using Sarvam AI TTS API.
* **`slide_renderer.py`**: Renders Marp markdown as PNG images using marp-cli.
* **`video_creator.py`**: Assembles the final video using ffmpeg to combine slide images with audio.

### UI Utility Modules

The `utils/` directory contains helper modules for the UI:

* **`ui_components.py`**: UI components such as step headers, status indicators, and preview displays.
* **`file_helpers.py`**: Utilities for file handling, uploads, and temporary storage.

### Running the UI

To run the Streamlit UI:

```bash
# Activate your virtual environment
source venv/bin/activate

# Set required API keys
export GEMINI_API_KEY="your-gemini-api-key"
export SARVAM_API_KEY="your-sarvam-api-key"

# Launch the Streamlit app
python -m streamlit run streamlit_app_enhanced.py
```

The UI provides:
- PDF upload interface
- API key configuration
- Process settings (max slides, slides-only mode)
- Real-time processing status with visual indicators
- Preview tabs for figures, slides, audio, and video
- Download options for all generated assets
- Debug logging view

## Dependencies

This project requires:

*   **Python 3.9+**: For all core functionality.
*   **Marp CLI**: For converting markdown into slide deck PNG frames. Install with `npm i -g @marp-team/marp-cli`.
*   **FFmpeg**: For creating the final video with audio. Install via your system's package manager (e.g., `apt install ffmpeg` on Ubuntu).
*   **Pip packages**: Install with `pip install -r requirements.txt` (after creating and activating a virtual environment).
*   **Streamlit**: For the web UI, included in requirements.txt.

## Troubleshooting

*   **`ModuleNotFoundError`**: Ensure your virtual environment is activated and all dependencies are installed (`pip install -r requirements.txt`).
*   **`marp` CLI not found**: Ensure Node.js and `marp-cli` are installed globally (`npm i -g @marp-team/marp-cli`).
*   **`ffmpeg` not found**: Ensure FFmpeg is installed on your system and accessible from your PATH.
*   **API Key Errors**: Double-check that your `GEMINI_API_KEY` and `SARVAM_API_KEY` environment variables are correctly set.
*   **"JSON file not found" Error**: This was a known issue that has been fixed. If you encounter this, ensure you're using the latest version of the code with the corrected file cleanup logic.
*   **Empty `frames/` directory or Blank Slides**: If Marp runs but no PNGs are generated, or you get an extra blank slide at the beginning or end, there may be an issue with the `deck.md` structure. The `json2marp.py` script is designed to prevent this, but if you modify it, ensure the front-matter (`---`) is correctly formatted and separated from the content.
*   **FFmpeg errors during video creation**: If you encounter errors related to audio streams or file durations, it may be due to inconsistencies in the WAV files produced by the TTS service. The scripts now include an audio pre-processing step to standardize the audio files before passing them to `ffmpeg`, which should prevent these issues.

Feel free to explore and modify the scripts to suit your specific needs!