# Paper Explainer

Convert any academic paper into a short, narrated slide-deck video – end-to-end, in one click.

Key capabilities (2025-07):
* 📑 PDF text extraction with Mistral OCR
* 🖼️ Figure detection & cropping with Mistral OCR
* ✨ LLM slide synthesis with Markdown + narration script
* 🔊 Sarvam AI TTS per-slide narration
* 🖼️→🎞️ Marp-CLI rendering to PNG frames
* 🎬 ffmpeg assembly into MP4
* 🌐 Streamlit UI with live step-by-step progress (⏳ → 🔄 → ✅)
* Flexible slide count (2-20) and *slides-only* fast-mode

---

# TODO

## Features
- [ ] Port to Ollama: gemma 3n
- [ ] When extracting test, index sections and chat with paper
- [ ] Improve Figure cropping: Drawing lines or finetuning


## Development
- [ ] Tests to test without UI
- [ ] Deploy on GCP

## Known Issues

*   **Marp CLI Browser Dependency**: The `txt2slides.py` script uses `npx marp` to render Markdown slides into PNG frames. Marp requires a headless browser (like Chromium) to do this. In some environments, a suitable browser may not be installed or detected, causing the script to fail with a `No suitable browser found` error. Future work should involve explicitly providing the path to a browser executable to the `marp` command (e.g., via the `--chrome-path` flag) or ensuring a browser is installed as part of the environment setup.


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

## Deployment (Systemd Service)

To run the Paper Explainer as a persistent background service on a Linux server, you can use the provided systemd service configuration. This ensures the application starts automatically on boot and restarts if it fails.

1.  **Generate the Service File**:
    The `install.sh` script generates a `paper-explainer.service` file tailored to your environment (correct user and project path).

    ```bash
    ./install.sh
    ```

2.  **Set Up Environment Variables**:
    Create an environment file to store your API keys securely.

    ```bash
    # Copy the example environment file
    sudo cp .env.example /etc/paper-explainer.env

    # Open the file with a text editor (e.g., nano) and add your API keys
    sudo nano /etc/paper-explainer.env

    # Secure the file so only the root user and its group can read it
    sudo chmod 600 /etc/paper-explainer.env
    ```

3.  **Install and Start the Service**:
    Move the generated service file to the systemd directory and start the service.

    ```bash
    # Move the service file
    sudo mv paper-explainer.service /etc/systemd/system/

    # Reload the systemd daemon to recognize the new service
    sudo systemctl daemon-reload

    # Enable the service to start on boot
    sudo systemctl enable paper-explainer.service

    # Start the service immediately
    sudo systemctl start paper-explainer.service
    ```

4.  **Check Service Status**:
    You can check the status of the service and view its logs to ensure it's running correctly.

    ```bash
    # Check the status
    sudo systemctl status paper-explainer.service

    # View the latest logs
    journalctl -u paper-explainer.service -f
    ```

## Core Components & What They Do

*   **`pdf2json.py`**: This file contains the `call_llm` helper function, which is responsible for sending prompts to the Gemini 2.5 Pro LLM and returning its raw JSON response. It handles authentication, retries, and model selection internally.

*   **`json2marp.py`**: This script takes the structured JSON output from the LLM (generated by `txt2slides.py`) and converts it into Marp Markdown format. Marp Markdown is a specialized Markdown syntax for creating slide decks, with built-in support for MathJax for rendering mathematical equations.

*   **Whitespace-compaction in `txt2slides.py`**: The script now automatically collapses unnecessary internal spaces, tabs, and blank lines in the prompts before sending them to Gemini. This reduces token usage while retaining readability. For debugging, the raw *and* compacted prompts are written to `slides/full_llm_prompt.txt` (which remains git-ignored by default).

*   **`extract_images_llm.py`**: Original Gemini-based figure extraction (legacy, replaced by Mistral OCR). This file is kept for reference but is no longer used in the main pipeline.

## 🔥 Mistral OCR Integration - Modern PDF Processing

The application now uses **Mistral OCR API** for superior PDF text and figure extraction with optimized single-call processing:

### **Core Mistral Components:**

*   **`mistral_config.py`**: Configuration file for Mistral OCR settings. Contains API key management (via environment variables), processing options, and feature flags. This centralizes all Mistral-related configuration.

*   **`extract_mistral_pdf.py`**: Low-level Mistral OCR interface script that sends PDFs to the Mistral OCR API and processes the response. Creates structured output with markdown text, extracted images, and JSON metadata for each page.

*   **`processors/mistral_unified_extractor.py`**: **Core extraction engine** - The heart of the Mistral integration. This class processes a PDF once with Mistral OCR and provides methods to extract both text and figures from the cached results. Implements intelligent figure title/caption extraction from markdown context.

*   **`processors/mistral_cache.py`**: Thread-safe caching system that ensures the same PDF is only processed once per session. When both text and figures are needed, the cache prevents duplicate API calls, saving costs and processing time.

*   **`processors/text_extractor.py`**: **Text extraction interface** - Now uses Mistral OCR via the unified extractor. Returns clean markdown text with preserved formatting and structure from the PDF.

*   **`processors/figure_extractor.py`**: **Figure extraction interface** - Now uses Mistral OCR via the unified extractor. Generates the expected `figures_metadata.json` format compatible with the existing slide generation pipeline.

### **Mistral Processing Flow:**
```
PDF Input → mistral_unified_extractor.py → Single Mistral OCR API Call
                                        ↓
                                   Cached Results
                                ↙               ↘
                    text_extractor.py    figure_extractor.py
                    (markdown text)      (figures + metadata)
                                ↘               ↙
                                   Slide Generation
```

### **Key Advantages:**
- **Single API Call**: Both text and figures extracted in one request
- **Superior OCR**: Better accuracy than vision-based extraction
- **Cost Efficient**: ~50% API cost reduction vs dual extraction
- **Markdown Output**: Structured text with preserved formatting
- **Automatic Cleanup**: Temporary files cleaned after processing

*   **`txt2slides.py`**: This is the main orchestration script for the entire pipeline. It performs the following steps:
    1.  Accepts either plain-text (`.txt`) or PDF (`.pdf`) files as input. For PDFs, it uses the Mistral OCR system to extract both text content and figures.
    2.  Text extraction via `processors/text_extractor.py` (now using Mistral OCR)
    3.  Figure extraction via `processors/figure_extractor.py` (now using Mistral OCR with shared cache)
    4.  Constructs a prompt for the Gemini LLM, instructing it to break the text into a specified number of slides with concise content and detailed audio narration.
    5.  Calls `pdf2json.py` to interact with the LLM and get the structured slide data.
    6.  Saves the raw LLM output as a JSON file (`slides/<original_filename>_slides_plan.json`).
    7.  Calls `json2marp.py` to convert the LLM's JSON into a Marp Markdown file (`slides/deck.md`), embedding the extracted figures.
    8.  Generates audio narration files (`slides/audio/slideXX.wav`) for each slide using Sarvam AI's Text-to-Speech (TTS) service.
    9.  Renders the Marp Markdown file into individual PNG image frames (`slides/frames/deck.00X.png`) using the `marp-cli` tool.
    10. Combines the generated PNG frames and audio files into a single MP4 video (`slides/video.mp4`) using `ffmpeg`).

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

### 3. Install Ollama (for Local LLM Usage)

Ollama is required to run local language models like Gemma for slide generation. The repository includes a script to install it on Linux.

```bash
# Make the script executable
chmod +x install.sh

# Run the installer
./install.sh
```

After installing Ollama, you need to pull the model you intend to use. For example, to use `gemma:3n-e4b`:
```bash
ollama pull gemma:3n-e4b
```

### 4. Install Node.js and Marp CLI

`marp-cli` is a Node.js package that converts Marp Markdown to various formats, including PNGs. It requires Node.js (version 18 or higher is recommended).

```bash
# Install Node.js (if not already installed) - refer to Node.js official documentation for your OS
# Example for Ubuntu:
# sudo apt update
# sudo apt install nodejs npm

# Install marp-cli globally
npm i -g @marp-team/marp-cli
```

### 5. Install FFmpeg

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

### 6. Set API Keys

This project uses API keys for Mistral OCR (for PDF processing), Gemini (for slide generation), and Sarvam AI (for TTS). **Never hardcode your API keys in the source code.** Instead, set them as environment variables.

*   **`MISTRAL_API_KEY`**: Your API key for Mistral OCR.
*   **`GEMINI_API_KEY`**: Your API key for Google Gemini (slide generation).
*   **`SARVAM_API_KEY`**: Your API key for Sarvam AI.

**Example (Linux/macOS):**

```bash
export MISTRAL_API_KEY="YOUR_MISTRAL_API_KEY"
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
export SARVAM_API_KEY="YOUR_SARVAM_API_KEY"
```

**Example (Windows Command Prompt):**

```cmd
set MISTRAL_API_KEY="YOUR_MISTRAL_API_KEY"
set GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
set SARVAM_API_KEY="YOUR_SARVAM_API_KEY"
```

For persistent environment variables, refer to your operating system's documentation.



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
export MISTRAL_API_KEY="your-mistral-api-key"
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

## Deployment

### Deployment on a Google Cloud Platform (GCP) VM

This section details the steps to deploy the Paper Explainer application as a persistent service on a Google Cloud Platform Compute Engine VM. This setup ensures the application starts automatically on boot, restarts if it crashes, and is accessible from the public internet via a standard HTTP port.

**Before you begin, replace all placeholders in angle brackets (e.g., `<YOUR_USER>`) with your specific values.**

- **VM Public IP Address:** `<YOUR_VM_IP_ADDRESS>`
- **GCP Project ID:** `<YOUR_GCP_PROJECT_ID>`
- **User:** `<YOUR_USER>`
- **Project Directory:** `/<PATH_TO_PROJECT_REPO>`

#### 1. System Dependencies and Project Setup

Before deploying, install the following system-level dependencies on the VM:

- **Node.js and npm:** Required for `marp-cli`.
- **FFmpeg:** Essential for video assembly.
- **python3.11-venv:** Required for creating Python virtual environments.

```bash
sudo apt-get update
sudo apt-get install -y nodejs npm ffmpeg python3.11-venv
```

Install the `marp-cli` Node.js package globally:
```bash
sudo npm i -g @marp-team/marp-cli
```

Create a Python virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. systemd Service for Streamlit Application

To run the Streamlit application persistently, create a `systemd` service.

**Purpose of `paper-explainer.service`:**
This file defines how the operating system manages the Streamlit application, ensuring it starts on boot, runs as your user, and restarts on failure.

- **File Location:** `/etc/systemd/system/paper-explainer.service`
- **Action:** Create the `paper-explainer.service` file in your project directory with the content below. **Remember to replace the placeholders.**

  ```ini
  [Unit]
  Description=Paper Explainer Streamlit Service
  After=network.target

  [Service]
  User=<YOUR_USER>
  Group=<YOUR_USER>
  WorkingDirectory=/<PATH_TO_PROJECT_REPO>
  # Recommended: Use EnvironmentFile for security
  # Create /etc/paper-explainer.env with your API keys
  # EnvironmentFile=/etc/paper-explainer.env
  Environment="GEMINI_API_KEY=<YOUR_GEMINI_API_KEY>"
  Environment="SARVAM_API_KEY=<YOUR_SARVAM_API_KEY>"
  # Note: Ensure the PATH includes the directory where npx is installed.
  # You can find it by running 'which npx' as the correct user.
  Environment="PATH=/home/<YOUR_USER>/.nvm/versions/node/v22.17.1/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
  ExecStart=/<PATH_TO_PROJECT_REPO>/venv/bin/streamlit run streamlit_app_enhanced.py --server.port 8502 --server.address 0.0.0.0
  Restart=always

  [Install]
  WantedBy=multi-user.target
  ```
  **Security Best Practice:** For managing API keys, it is highly recommended to use the `EnvironmentFile` directive. Create a file at `/etc/paper-explainer.env` with the following content:
  ```
  GEMINI_API_KEY=<YOUR_GEMINI_API_KEY>
  SARVAM_API_KEY=<YOUR_SARVAM_API_KEY>
  ```
  Then, in your `paper-explainer.service` file, replace the `Environment` lines for the keys with `EnvironmentFile=/etc/paper-explainer.env`. Make sure to secure this file with `sudo chmod 600 /etc/paper-explainer.env`.

**Deployment Steps for `systemd` service:**

Copy the service file to the systemd directory:
```bash
sudo cp /<PATH_TO_PROJECT_REPO>/paper-explainer.service /etc/systemd/system/paper-explainer.service
```

Reload the systemd daemon, enable the service to start on boot, and start it:
```bash
sudo systemctl daemon-reload
sudo systemctl enable paper-explainer.service
sudo systemctl start paper-explainer.service
```

**`update_service.sh` Script:**
This helper script automates updating the service. **Remember to replace the placeholder.**
  ```bash
  #!/bin/bash
  set -e
  echo "1. Copying the updated systemd service file..."
  sudo cp /<PATH_TO_PROJECT_REPO>/paper-explainer.service /etc/systemd/system/paper-explainer.service
  echo "2. Reloading the systemd daemon..."
  sudo systemctl daemon-reload
  echo "3. Restarting the Paper Explainer service..."
  sudo systemctl restart paper-explainer.service
  echo "Done."
  ```

#### 3. Nginx Reverse Proxy for Public Access

Set up Nginx as a reverse proxy to make the application accessible on port 80.

**Nginx Installation:**
```bash
sudo apt-get update
sudo apt-get install -y nginx
```

**Purpose of `paper-explainer-nginx.conf`:**
This Nginx configuration file forwards public traffic from port 80 to the internal Streamlit application on port 8502.

- **File Location:** `/etc/nginx/sites-available/paper-explainer.conf`
- **Action:** Create `paper-explainer-nginx.conf` in your project directory. **Replace the placeholder.**

  ```nginx
  server {
      listen 80;
      server_name <YOUR_VM_IP_ADDRESS>;
      client_max_body_size 100M;

      location / {
          proxy_pass http://127.0.0.1:8502;
          proxy_http_version 1.1;
          proxy_set_header Upgrade $http_upgrade;
          proxy_set_header Connection "upgrade";
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }

      location /healthz {
          proxy_pass http://127.0.0.1:8502/healthz;
      }

      location /static {
          proxy_pass http://127.0.0.1:8502/static;
      }
  }
  ```

**Deployment Steps for Nginx:**

Remove the default Nginx configuration:
```bash
sudo rm /etc/nginx/sites-enabled/default
```

Copy the new configuration and create a symlink to enable it:
```bash
sudo cp /<PATH_TO_PROJECT_REPO>/paper-explainer-nginx.conf /etc/nginx/sites-available/paper-explainer.conf
sudo ln -s /etc/nginx/sites-available/paper-explainer.conf /etc/nginx/sites-enabled/
```

Test the Nginx configuration and restart the service:
```bash
sudo nginx -t
sudo systemctl restart nginx
```

**`update_nginx.sh` Script:**
This script automates updating the Nginx configuration. **Replace the placeholder.**
  ```bash
  #!/bin/bash
  set -e
  echo "1. Copying the updated Nginx configuration file..."
  sudo cp /<PATH_TO_PROJECT_REPO>/paper-explainer-nginx.conf /etc/nginx/sites-available/paper-explainer.conf
  echo "2. Testing the Nginx configuration..."
  sudo nginx -t
  echo "3. Restarting Nginx..."
  sudo systemctl restart nginx
  echo "Done."
  ```

#### 4. Firewall Configuration (VM Host & GCP)

Allow public access to port 80 through the host and GCP firewalls.

**On-Host Firewall (`iptables`):**
```bash
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -D INPUT -p tcp --dport 8502 -j ACCEPT # Remove old rule if it exists
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save
```

**GCP Cloud Firewall:**
Run these `gcloud` commands from your local machine or Cloud Shell. **Replace the placeholder.**
```bash
gcloud compute firewall-rules create paper-explainer-allow-http \
    --project=<YOUR_GCP_PROJECT_ID> \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:80 \
    --source-ranges=0.0.0.0/0

gcloud compute firewall-rules delete paper-explainer-allow-8502 --quiet
```

#### 5. Updating the Deployment

To apply changes to your application or configuration, use the update scripts:

- **To update the Streamlit service:**
  ```bash
  ./update_service.sh
  ```

- **To update the Nginx configuration:**
  ```bash
  ./update_nginx.sh
  ```
