# Paper Explainer

This project automates the process of converting academic papers (PDFs or any long-form text) into concise, narrated video presentations. It leverages Large Language Models (LLMs) to summarize content into slide-friendly formats, Text-to-Speech (TTS) for narration, and various tools for generating visual slides and combining them with audio into a video.

# TODO
1. ~~communication with LLM about figures and location is messed up. Handle that~~
 - ~~first see where and how figures are stored~~
 - ~~modify prompt to include figures whenever relevant~~

2. ~~Format text to LLM for creating slides.~~

2. Improve deck creation by more detailed prompt

3. Improve figure cropping 

4. get sub figure cropping

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

The process is a two-step pipeline to ensure figures are included correctly.

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

## Troubleshooting

*   **`ModuleNotFoundError`**: Ensure your virtual environment is activated and all dependencies are installed (`pip install -r requirements.txt`).
*   **`marp` CLI not found**: Ensure Node.js and `marp-cli` are installed globally (`npm i -g @marp-team/marp-cli`).
*   **`ffmpeg` not found**: Ensure FFmpeg is installed on your system and accessible from your PATH.
*   **API Key Errors**: Double-check that your `GEMINI_API_KEY` and `SARVAM_API_KEY` environment variables are correctly set.
*   **Empty `frames/` directory or Blank Slides**: If Marp runs but no PNGs are generated, or you get an extra blank slide at the beginning or end, there may be an issue with the `deck.md` structure. The `json2marp.py` script is designed to prevent this, but if you modify it, ensure the front-matter (`---`) is correctly formatted and separated from the content.
*   **FFmpeg errors during video creation**: If you encounter errors related to audio streams or file durations, it may be due to inconsistencies in the WAV files produced by the TTS service. The scripts now include an audio pre-processing step to standardize the audio files before passing them to `ffmpeg`, which should prevent these issues.

Feel free to explore and modify the scripts to suit your specific needs!