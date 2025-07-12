import os
import shutil
import json
import time
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

def analyze_image_with_gemini(image_path: str):
    """Sends an image to Gemini and asks it to identify figure bounding boxes."""
    print(f"Analyzing {Path(image_path).name} with Gemini...")
    
    system_prompt = """
    You are an expert in scientific document analysis. Your task is to analyze this image of a page from an academic paper.
    Identify all figures on this page. Do not include tables, text blocks, or page numbers unless they are part of a figure.
    For each figure you find, provide its bounding box coordinates. The coordinates must be normalized from 0.0 to 1.0, where (0.0, 0.0) is the top-left corner and (1.0, 1.0) is the bottom-right corner.
    
    Respond with a single, valid JSON object. The object must have a single key named 'figures'. The value of 'figures' should be a list of objects, where each object represents a single figure and has the following keys: 'x0', 'y0', 'x1', 'y1'.

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
    
    model = genai.GenerativeModel('gemini-1.5-pro-latest', system_instruction=system_prompt)
    image = Image.open(image_path)

    try:
        response = model.generate_content(image)
        # Clean up the response to extract only the JSON part
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"Error calling Gemini API or parsing JSON for {image_path}: {e}")
        return {"figures": []}

def extract_figures_from_llm_data(pdf_path: str, llm_data: dict, output_dir: str):
    """Crops figures from the PDF using coordinates from the LLM."""
    print("\nCropping figures based on LLM data...")
    extracted_files = []
    figure_counter = 1
    try:
        doc = fitz.open(pdf_path)
        # llm_data is a dict where keys are page numbers (1-based)
        for page_num, figures in tqdm(llm_data.items(), desc="Cropping figures"):
            page = doc.load_page(page_num - 1) # fitz is 0-indexed
            for fig_data in figures:
                # The LLM returns normalized coordinates, so we convert them
                # to pixel coordinates for cropping.
                rect = fitz.Rect(
                    fig_data['x0'] * page.rect.width,
                    fig_data['y0'] * page.rect.height,
                    fig_data['x1'] * page.rect.width,
                    fig_data['y1'] * page.rect.height
                )
                
                # Crop the figure
                pix = page.get_pixmap(clip=rect, dpi=300)
                
                # Save the figure
                output_filename = f"figure-{figure_counter}.png"
                output_path = Path(output_dir) / output_filename
                pix.save(output_path)
                extracted_files.append(str(output_path))
                figure_counter += 1
        doc.close()
        print(f"Successfully cropped and saved {len(extracted_files)} figures.")
        return extracted_files
    except Exception as e:
        print(f"Error during figure cropping: {e}")
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

        # Add a delay to avoid hitting API rate limits. The free tier is very strict.
        time.sleep(10)

    # 3. Crop figures based on LLM data
    extracted_files = extract_figures_from_llm_data(pdf_path, all_llm_data, output_dir)

    # 4. Clean up temporary page images
    print("Cleaning up temporary page images...")
    shutil.rmtree(temp_dir)

    print(f"--- LLM Figure Extraction Finished ---")
    return extracted_files

# --- Standalone Execution ---

if __name__ == "__main__":
    # We'll test with the eLife paper that failed before
    pdf_to_test = "/home/ragha/code/paper_agent_2/pdf_input/paper3.pdf"
    output_dir_test = "extracted_figures_llm_paper3"

    extracted = extract_figures_llm(pdf_to_test, output_dir_test, max_pages_to_process=6)

    if extracted:
        print("\n--- Summary ---")
        print("Successfully extracted the following files:")
        for f in extracted:
            print(f" - {f}")
    else:
        print("\n--- Summary ---")
        print("Extraction did not yield any files.")
