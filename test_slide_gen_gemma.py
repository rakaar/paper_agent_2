# Works Page by page
import os
import sys
import json
import re
import fitz  # PyMuPDF

# Add project root to path to allow importing from other modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from ollama import Client

# --- Helper functions copied from processors/llm_processor.py ---

def compact_whitespace(text: str) -> str:
    """Return `text` with internal whitespace collapsed to save LLM tokens."""
    lines = []
    prev_blank = False
    UNICODE_SPACES = ["\u00A0", "\u2002", "\u2003", "\u2009"]
    
    for raw in text.splitlines():
        for u in UNICODE_SPACES:
            raw = raw.replace(u, " ")
        stripped = raw.strip()
        stripped = re.sub(r"\s+", " ", stripped)
        if stripped == "":
            if not prev_blank:
                lines.append("")
            prev_blank = True
        else:
            lines.append(stripped)
            prev_blank = False
    return "\n".join(lines).strip()

def run_test():
    """Main test function."""

    # 2. Extract text from the first 2 pages of the PDF
    pdf_path = "full_paper.pdf"
    pages_to_process = 1
    extracted_text = ""
    print(f"--- Extracting text from first {pages_to_process} pages of {pdf_path} ---")
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(min(len(doc), pages_to_process)):
            page = doc[page_num]
            extracted_text += page.get_text()
        doc.close()
        print(f"--- Text extraction successful. Total characters: {len(extracted_text)} ---")
    except Exception as e:
        print(f"Error during PDF processing: {e}")
        return

    # 3. Generate slides
    print("--- Generating slides using Gemini... ---")
    
    # Compact the text to save tokens
    compacted_text = compact_whitespace(extracted_text)
    
    # --- Define Prompts (copied from processors/llm_processor.py for identical testing) ---
    system_prompt = """You are an AI assistant role-playing as a graduate student in a lab meeting, explaining an interesting paper to your peers.
Your tone should be conversational, insightful, and slightly informal. Refer to the paper's authors as 'the authors' or 'the paper,' not 'we'.

Your task is to create a JSON object that represents the slide deck. The JSON object should be a list of slides.
Each slide should have a "slide number", a "title", a "content" field, and an "audio" field.
The "content" field should contain the text for the slide body as a single string, formatted in Markdown.
The "audio" field should contain the narration script for the slide, matching your persona.

IMPORTANT: The output MUST be a single, valid JSON object. Ensure that all strings are properly escaped. For example, use \n for newlines within the content and audio strings, and escape any double quotes. Do not add any extra text or formatting outside of the JSON object itself. The entire response should be parseable by a standard JSON parser."""

    max_slides = 5
    # For this text-only test, we provide an empty instruction for figures.
    figures_prompt_injection = "No figures are available for this text. Do not attempt to embed any."

    user_prompt = f"""**IMPORTANT:** First, review the list of available figures. You MUST embed these figures in the 'content' of relevant slides.
{figures_prompt_injection}

Now, please break the following text into exactly {max_slides} slides. Each slide must be a JSON object with these exact keys: "slide number", "title", "content", and "audio".
- "slide number": An integer for the slide order.
- "title": A concise title for the slide.
- "content": Keep this extremely minimal:
        * If the slide EMBEDS A FIGURE, use **max 2 short bullet points or <=120 characters**.
        * Otherwise 3-4 bullets or brief paragraph. This is for on-screen text only.
- "audio": This should contain the full, detailed narration for the slide, suitable for text-to-speech. Maximize information transfer here.

Do not include any text, prose, or markdown formatting outside of the main JSON array.

Here is the text to process:
---
{compacted_text}
---
"""

    try:
        # Call the Ollama model
        cli = Client(timeout=300) # 5 minute timeout
        response = cli.chat(
            model='gemma3n:e4b',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            options={'temperature': 0},
            format='json' # Request JSON output
        )

        print("--- Successfully received response from Ollama ---")
        print("\n--- Generated Slides JSON ---")

        # The response content should already be a JSON object when format='json'
        slides_json_str = response.get('message', {}).get('content', '{}')
        
        try:
            # Try to parse and pretty-print the JSON
            parsed_json = json.loads(slides_json_str)
            print(json.dumps(parsed_json, indent=2))
        except json.JSONDecodeError:
            print("Warning: Ollama output was not valid JSON. Printing raw output:")
            print(slides_json_str)

    except Exception as e:
        print(f"An error occurred while calling Ollama: {e}")
        print("Please ensure the Ollama server is running and the 'gemma:3n-e4b' model is available.")

if __name__ == "__main__":
    run_test()
