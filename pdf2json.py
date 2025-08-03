import argparse
import json
import os
import io
import fitz  # PyMuPDF
from PIL import Image
from pydantic import BaseModel, Field, ValidationError
from typing import List, Literal, Optional
import google.generativeai as genai
import time
import ollama

# Pydantic Models for LLM response validation
class Block(BaseModel):
    id: str = Field(..., description="unique within document")
    type: Literal["section_title", "paragraph", "figure_caption", "table_caption", "equation"]
    text: str = Field(..., description="no linebreak hyphens, LaTeX for equations")
    page: int = Field(..., description="1-based")
    bbox: Optional[List[float]] = Field(None, description="PDF points or null if unknown")

class LLMResponse(BaseModel):
    blocks: List[Block]

def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Returns Gemini’s raw JSON response as string"""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    
    genai.configure(api_key=gemini_api_key)
    # Use JSON mode for robust parsing
    model = genai.GenerativeModel(
        'gemini-2.5-pro', 
        system_instruction=system_prompt,
        generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
    )

    for attempt in range(2): # One retry
        try:
            response = model.generate_content(user_prompt)
            # The response.text will be a valid JSON string because of the response_mime_type
            return response.text
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            if attempt == 0:
                print("  Retrying...")
                time.sleep(5)
            else:
                raise # Re-raise the exception if max retries reached

def call_ollama_llm(system_prompt: str, user_prompt: str) -> list:
    """Calls the Ollama model, expects a JSON response, and returns a list of slides."""
    try:
        response = ollama.chat(
            model='gemma3n:e4b',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ]
            # Removed format='json' to preserve markdown syntax in content
        )
        response_content = response['message']['content']
        print(f"Raw Ollama response length: {len(response_content)}")
        
        # TEMPORARY DEBUG LOGGING - Save raw response to file
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"/tmp/ollama_debug_{timestamp}.log"
        
        try:
            with open(log_filename, 'w', encoding='utf-8') as log_file:
                log_file.write("=== OLLAMA DEBUG LOG ===\n")
                log_file.write(f"Timestamp: {timestamp}\n")
                log_file.write(f"Response length: {len(response_content)}\n")
                log_file.write("=== SYSTEM PROMPT ===\n")
                log_file.write(system_prompt)
                log_file.write("\n\n=== USER PROMPT ===\n")
                log_file.write(user_prompt)
                log_file.write("\n\n=== RAW OLLAMA RESPONSE ===\n")
                log_file.write(response_content)
                log_file.write("\n\n=== END LOG ===\n")
            print(f"🔍 DEBUG: Saved raw Ollama response to {log_filename}")
        except Exception as log_error:
            print(f"Warning: Could not save debug log: {log_error}")
        
        # Extract JSON from the raw response with multiple strategies
        import re
        json_str = None
        
        # Strategy 1: Look for JSON in code blocks
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_content, re.DOTALL)
        if code_block_match:
            json_str = code_block_match.group(1)
            print("Found JSON in code block")
        
        # Strategy 2: Look for JSON object starting with { and ending with }
        if not json_str:
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                print("Found JSON object in response")
        
        # Strategy 3: Try the entire response as JSON
        if not json_str:
            json_str = response_content.strip()
            print("Using entire response as JSON")
        
        # Clean up the JSON string
        json_str = json_str.strip()
        
        # Try to parse the JSON
        try:
            parsed_json = json.loads(json_str)
        except json.JSONDecodeError as e:
            # If parsing fails, try to fix common issues
            print(f"Initial JSON parsing failed: {e}")
            print(f"Attempting to fix JSON string...")
            
            # Remove any leading/trailing non-JSON content
            json_str = re.sub(r'^[^{]*', '', json_str)  # Remove everything before first {
            json_str = re.sub(r'[^}]*$', '', json_str[::-1])[::-1]  # Remove everything after last }
            
            # Try parsing again
            parsed_json = json.loads(json_str)

        # Check if the response is a dictionary containing the 'slides' key
        if isinstance(parsed_json, dict) and 'slides' in parsed_json and isinstance(parsed_json['slides'], list):
            print(f"✅ Successfully extracted {len(parsed_json['slides'])} slides from response")
            # Debug: Show first slide content to verify format
            if parsed_json['slides']:
                first_slide = parsed_json['slides'][0]
                content = first_slide.get('content', '')
                has_figures = '![' in content and '](' in content
                print(f"🔍 First slide has figures: {has_figures}")
                if not has_figures:
                    print(f"⚠️  First slide content preview: {content[:200]}...")
            return parsed_json['slides']
        # Handle the case where the response is already a list (for robustness)
        elif isinstance(parsed_json, list):
            print(f"✅ Response is already a list with {len(parsed_json)} items")
            return parsed_json
        else:
            print(f"❌ ERROR: Ollama response was not in the expected format (dict with 'slides' or a list).")
            print(f"Response type: {type(parsed_json)}")
            print(f"Response keys: {list(parsed_json.keys()) if isinstance(parsed_json, dict) else 'Not a dict'}")
            print(f"Raw parsed JSON: {str(parsed_json)[:500]}...")
            return []

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from Ollama response: {e}")
        print(f"Raw response (first 1000 chars): {response_content[:1000]}...")
        print(f"Attempted JSON string: {json_str[:500] if json_str else 'None'}...")
        return []
    except Exception as e:
        print(f"Error calling Ollama or processing its response: {e}")
        if 'response_content' in locals():
            print(f"Raw response (first 500 chars): {response_content[:500]}...")
        return []

def process_pdf(pdf_path: str, output_path: str, api_key: str):
    """
    Processes a PDF, extracts structured information using an LLM, and saves it as JSON.
    """
    # The system instruction is provided directly in the prompt.
    system_prompt = """You are a scientific PDF parser. For each page image, return ONLY the main text and mathematical expressions present on that page, as plain text. IGNORE ALL figure captions and any text associated with figures—do not include them in the output. For ALL mathematical expressions, write them in LaTeX and wrap them in <formula>...</formula> tags (for display or standalone equations). For inline math inside paragraphs, use $...$ LaTeX as normal. The output should be suitable for saving as a .txt file for each page. Output only the text content, nothing else."""

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return

    total_pages = doc.page_count

    for page_num in range(total_pages):
        print(f"Processing page {page_num + 1}/{total_pages}...")
        page = doc.load_page(page_num)

        # Render page to PNG image at 220 DPI
        pix = page.get_pixmap(matrix=fitz.Matrix(220/72, 220/72))
        img_bytes = pix.tobytes("png")

        # Prepare image for LLM
        image_part = {
            "mime_type": "image/png",
            "data": img_bytes
        }

        page_text = None
        try:
            page_text = call_llm(system_prompt, [image_part]) # Pass image_part as user_prompt
        except Exception as e:
            print(f"  LLM call failed for page {page_num + 1}: {e}")

        if page_text:
            txt_filename = os.path.splitext(output_path)[0] + f"_page_{page_num+1}.txt"
            try:
                with open(txt_filename, 'w', encoding='utf-8') as f:
                    f.write(page_text)
            except Exception as e:
                print(f"Error saving text for page {page_num+1}: {e}")

    print(f"Successfully processed PDF and saved text pages with base name {output_path}")

def main():
    """
    Main function to parse arguments and initiate PDF processing.

    Example usage:
    python pdf2json.py --pdf paper.pdf --out paper_structured.json
    """
    parser = argparse.ArgumentParser(description="Convert a PDF to structured JSON using an LLM.")
    parser.add_argument("--pdf", required=True, help="Path to the input PDF file.")
    parser.add_argument("--out", required=True, help="Path to the output JSON file.")
    args = parser.parse_args()

    process_pdf(args.pdf, args.out, "") # API key is now handled by call_llm

if __name__ == "__main__":
    main()
