import os
import shutil
import json
import time
import argparse
from pathlib import Path
import fitz  # PyMuPDF
import google.generativeai as genai
from PIL import Image
from tqdm import tqdm

# --- Configuration ---
# Ensure the Gemini API key is set in your environment variables
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
except AttributeError:
    print("Error: The GEMINI_API_KEY environment variable is not set.")
    exit()

# --- Core Functions ---

def pdf_to_images(pdf_path: str, temp_dir: str, dpi: int = 300, max_pages: int = None):
    """Converts each page of a PDF into a high-resolution image."""
    print(f"Converting PDF pages to images (at {dpi} DPI)...")
    image_paths = []
    try:
        doc = fitz.open(pdf_path)
        
        num_pages_to_process = len(doc)
        if max_pages is not None and max_pages < len(doc):
            print(f"Limiting processing to the first {max_pages} pages.")
            num_pages_to_process = max_pages

        for page_num in tqdm(range(num_pages_to_process), desc="Rendering pages"):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=dpi)
            image_path = Path(temp_dir) / f"page_{page_num + 1}.png"
            pix.save(image_path)
            image_paths.append(str(image_path))
        doc.close()
        print("PDF to image conversion complete.")
        return image_paths
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        return []

def analyze_image_with_gemini(image_path: str, max_retries=5, initial_backoff=2):
    """Sends an image to Gemini with exponential backoff to handle rate limits."""
    print(f"Analyzing {Path(image_path).name} with Gemini...")

    system_prompt = """
    You are an expert in scientific document analysis. Your task is to analyze this image of a page from an academic paper.
    Identify all complete figures on this page. A 'figure' is a visual element, often composed of multiple sub-plots or panels.
    
    For each figure you find, you must extract three pieces of information:
    1. The bounding box of the visual part of the figure. This box should generously encompass all sub-plots, panels, axes, and integrated labels (e.g., 'A', 'B', 'C'). It must EXCLUDE the figure's title and caption text, which are typically located below the graphic.
    2. The figure's title (e.g., "Figure 1", "Figure 2: Simulation results").
    3. The figure's caption (the full descriptive text accompanying the figure).

    The coordinates must be normalized from 0.0 to 1.0, where (0.0, 0.0) is the top-left corner.

    Respond with a single, valid JSON object. The object must have a single key named 'figures'. The value of 'figures' should be a list of objects, where each object represents a single, complete figure and has the following keys: 'x0', 'y0', 'x1', 'y1', 'title', 'caption'.

    Example response:
    ```json
    {
      "figures": [
        {
          "x0": 0.1,
          "y0": 0.2,
          "x1": 0.4,
          "y1": 0.5,
          "title": "Figure 1: Model Architecture",
          "caption": "An overview of the model architecture, showing the different layers and connections."
        }
      ]
    }
    ```
    If there are no figures on the page, return an empty list: `{"figures": []}`.

    Example response for a page with two figures:
    ```json
    {
      "figures": [
        {
          "x0": 0.1,
          "y0": 0.2,
          "x1": 0.4,
          "y1": 0.5
        },
        {
          "x0": 0.6,
          "y0": 0.2,
          "x1": 0.9,
          "y1": 0.5
        }
      ]
    }
    ```
    If there are no figures on the page, return an empty list: `{"figures": []}`.
    Do not include any other text, explanations, or markdown formatting in your response. Your entire response must be only the raw JSON object.
    """

    model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=system_prompt)

    try:
        # Prepare the image in the format the API expects
        print(f"  Reading image file: {image_path}")
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        image_part = {
            "mime_type": "image/png",
            "data": image_bytes
        }
        print("  Image data prepared successfully.")
    except Exception as e:
        print(f"Error reading or preparing image file {image_path}: {e}")
        return {"figures": []}

    for attempt in range(max_retries):
        try:
            print("  Attempting to call Gemini API...")
            response = model.generate_content([image_part])
            print("  Gemini API call successful. Processing response...")
            
            # Log the raw response for debugging
            print(f"  Raw response text: {response.text}")
            
            # Clean the response to extract only the JSON object
            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            # Handle empty responses after cleaning
            if not cleaned_text:
                print("  Warning: Received empty response from API.")
                return {"figures": []}

            # Attempt to parse the JSON
            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError as json_err:
                print(f"  Error: Failed to decode JSON. The response may be malformed.")
                print(f"  JSONDecodeError: {json_err}")
                print(f"  Problematic text: {cleaned_text}")
                return {"figures": []} # Return empty to avoid crashing
        except Exception as e:
            # Specific check for 429 Resource Exhausted error
            if "429" in str(e) and attempt < max_retries - 1:
                wait_time = initial_backoff * (2 ** attempt)
                print(f"  Rate limit hit on attempt {attempt + 1}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Error calling Gemini API or parsing JSON for {image_path} on attempt {attempt + 1}: {e}")
                return {"figures": []}
    print(f"Failed to analyze {image_path} after {max_retries} retries.")
    return {"figures": []}

def extract_figures_from_llm_data(pdf_path: str, llm_data: dict, output_dir: str):
    """Crops figures and saves their metadata as JSON files."""
    print("\nCropping figures and generating metadata based on LLM data...")
    extracted_files = []
    figure_counter = 1
    try:
        doc = fitz.open(pdf_path)
        for page_num, figures in tqdm(llm_data.items(), desc="Cropping figures"):
            page = doc.load_page(page_num - 1) # fitz is 0-indexed
            for fig_data in figures:
                # --- Coordinate Normalization ---
                x0, y0, x1, y1 = fig_data.get('x0', 0), fig_data.get('y0', 0), fig_data.get('x1', 0), fig_data.get('x1', 0)

                if x0 > 1.0 or y0 > 1.0 or x1 > 1.0 or y1 > 1.0:
                    print(f"  Detected pixel-based coordinates on page {page_num}. Normalizing...")
                    x0 /= page.rect.width
                    y0 /= page.rect.height
                    x1 /= page.rect.width
                    y1 /= page.rect.height

                rect = fitz.Rect(x0 * page.rect.width, y0 * page.rect.height, x1 * page.rect.width, y1 * page.rect.height)
                
                # --- Save Figure Image ---
                pix = page.get_pixmap(clip=rect, dpi=300)
                png_filename = f"figure-{figure_counter}.png"
                output_path = Path(output_dir) / png_filename
                pix.save(output_path)
                extracted_files.append(str(output_path))

                # --- Save Figure Metadata ---
                metadata = {
                    "figure_id": figure_counter,
                    "page_num": page_num,
                    "title": fig_data.get("title", ""),
                    "caption": fig_data.get("caption", ""),
                    "png_filename": png_filename
                }
                json_filename = f"figure-{figure_counter}.json"
                json_output_path = Path(output_dir) / json_filename
                with open(json_output_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=4)

                figure_counter += 1
        doc.close()
        print(f"Successfully cropped and saved {len(extracted_files)} figures and their metadata.")
        return extracted_files
    except Exception as e:
        print(f"Error during figure cropping or metadata generation: {e}")
        return []

# --- Main Pipeline ---

def extract_figures_llm(pdf_path: str, output_dir: str, max_pages_to_process: int = None):
    """Main pipeline to extract figures from a PDF using an LLM."""
    print(f"--- Starting LLM Figure Extraction for {pdf_path} ---")
    base_name = Path(pdf_path).stem
    temp_dir = Path(output_dir) / f"{base_name}_temp_pages"

    # Clean up previous runs and create directories
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    os.makedirs(temp_dir, exist_ok=True)

    # 1. Convert PDF to images
    image_paths = pdf_to_images(pdf_path, str(temp_dir), max_pages=max_pages_to_process)
    if not image_paths:
        return []

    # 2. Analyze each image with the LLM
    all_llm_data = {}
    for i, img_path in enumerate(image_paths):
        page_num = i + 1
        llm_result = analyze_image_with_gemini(img_path)
        if llm_result and llm_result.get("figures"):
            all_llm_data[page_num] = llm_result["figures"]

    # 3. Crop figures based on LLM data
    extracted_files = extract_figures_from_llm_data(pdf_path, all_llm_data, output_dir)

    # 4. Clean up temporary page images
    print("Cleaning up temporary page images...")
    shutil.rmtree(temp_dir)

    print(f"--- LLM Figure Extraction Finished ---")
    return extracted_files

# --- Standalone Execution ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract figures and metadata from a PDF file using a vision LLM.")
    parser.add_argument("pdf_path", type=str, help="The path to the PDF file to process.")
    parser.add_argument("--output_dir", type=str, default=None, help="Optional. The directory to save extracted files. Defaults to 'extracted_figures_llm_<pdf_name>'.")
    parser.add_argument("--max_pages", type=int, default=None, help="Optional. The maximum number of pages to process.")
    args = parser.parse_args()

    # If output directory is not specified, create a default one based on the PDF name
    output_dir = args.output_dir
    if not output_dir:
        pdf_name = Path(args.pdf_path).stem
        output_dir = f"extracted_figures_llm_{pdf_name}"

    # Run the main extraction function
    extracted = extract_figures_llm(
        pdf_path=args.pdf_path, 
        output_dir=output_dir, 
        max_pages_to_process=args.max_pages
    )

    if extracted:
        print("\n--- Summary ---")
        print("Successfully extracted the following files:")
        for f in extracted:
            print(f" - {f}")
    else:
        print("\n--- Summary ---")
        print("Extraction did not yield any files.")
