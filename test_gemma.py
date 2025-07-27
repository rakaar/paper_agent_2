## VISION ENCODER ISSUES?
import base64
import os
import sys
import json
from ollama import Client
from PIL import Image, ImageOps

def run_gemma_test():
    """Runs a test to extract structured figure data from an image using Gemma."""
    pdf_path = 'full_paper.pdf'  # PDF to render
    page_num = 3               # 1-based page number to test
    image_path = f'page_{page_num}.png'

    if not os.path.exists(image_path):
        # Try rendering the page from the PDF
        try:
            import fitz  # PyMuPDF
        except ImportError:
            print("PyMuPDF is not installed in the venv. Run 'pip install --upgrade PyMuPDF' inside venv.")
            return

        if not os.path.exists(pdf_path):
            print(f"Error: PDF '{pdf_path}' not found.")
            return

        print(f"Rendering page {page_num} of '{pdf_path}' to '{image_path}' …")
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_num - 1)  # 0-based index
            pix  = page.get_pixmap(dpi=450)  # higher DPI per checklist
            pix.save(image_path)
            doc.close()
            # Down-sample / pad to 896×896 for Gemma vision
            page_img = Image.open(image_path)
            # Resize while maintaining aspect ratio
            page_img.thumbnail((896, 896), Image.Resampling.BICUBIC)
            page_img.save(image_path)
            print("Rendering complete and resized to 896×896 for Gemma.")
        except Exception as e:
            print(f"Failed to render PDF page: {e}")
            return

    system_prompt = "You are an expert OCR assistant. Your only task is to extract any and all text from the given image, in the correct reading order. Do not add any commentary or formatting."

    print(f"Reading and encoding image: {image_path}")
    try:
        with open(image_path, "rb") as f:
            b64_image = base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"Error reading image file: {e}")
        return

    print("Sending request to local Gemma model...")
    try:
        cli = Client(timeout=300)  # 5 minute timeout
        response = cli.chat(
            model='gemma3:12b-it-qat',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {
                    'role': 'user',
                    'content': 'Read the text in this image.',
                    'images': [b64_image]
                }
            ],
            options={'temperature': 0, 'num_gpu': -1},

        )

        print("\n--- Gemma OCR Output ---")
        # Add a debug print to see the full response object
        print(f"[DEBUG] Full response object:\n{response}")

        raw_content = response.get('message', {}).get('content', '[[[NO CONTENT RETURNED]]]')
        print(raw_content)
        print("-----------------------------")
        return

        print("\n--- Extracted Figures ---")
        if data.get('figures'):
            # Open the original image to be cropped
            source_image = Image.open(image_path)
            img_width, img_height = source_image.size

            for i, fig_data in enumerate(data['figures']):
                print(f"  Figure {i+1}:")
                print(f"    Title: {fig_data.get('title', 'N/A')}")
                print(f"    Caption: {fig_data.get('caption', 'N/A')}")

                # --- Coordinate Normalization (mimicking extract_images_llm.py) ---
                x0, y0, x1, y1 = fig_data.get('x0', 0), fig_data.get('y0', 0), fig_data.get('x1', 0), fig_data.get('y1', 0)
                
                if x0 > 1.0 or y0 > 1.0 or x1 > 1.0 or y1 > 1.0:
                    print(f"  Detected pixel-based coordinates. Normalizing...")
                    x0 /= img_width
                    y0 /= img_height
                    x1 /= img_width
                    y1 /= img_height

                print(f"    Bounding Box (Normalized): [x0={x0:.4f}, y0={y0:.4f}, x1={x1:.4f}, y1={y1:.4f}]")

                # Convert normalized coordinates to absolute pixel coordinates
                px_box = (x0 * img_width, y0 * img_height, x1 * img_width, y1 * img_height)
                
                # Crop the image
                cropped_image = source_image.crop(px_box)
                
                # Save the cropped image
                output_filename = f"cropped_figure_{i+1}.png"
                cropped_image.save(output_filename)
                print(f"    -> Successfully cropped and saved to '{output_filename}'")
        else:
            print("No figures were found in the response.")
        print("-------------------------")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please ensure the Ollama server is running and the 'gemma3n:e4b' model is available.")

if __name__ == "__main__":
    run_gemma_test()
