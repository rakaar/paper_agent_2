import os
import json
import sys
from pathlib import Path

sys.path.append(os.path.abspath('.'))  # Add project root to path
from pdf2json import call_llm
import re

def compact_whitespace(text: str) -> str:
    """Return `text` with internal whitespace collapsed to save LLM tokens."""
    lines = []
    prev_blank = False
    UNICODE_SPACES = ["\u00A0", "\u2002", "\u2003", "\u2009"]
    
    for raw in text.splitlines():
        # Replace special unicode spaces
        for u in UNICODE_SPACES:
            raw = raw.replace(u, " ")
        stripped = raw.strip()
        # Collapse internal whitespace (incl. tabs) to single space
        stripped = re.sub(r"\s+", " ", stripped)
        if stripped == "":
            if not prev_blank:
                lines.append("")  # keep a single blank line
            prev_blank = True
        else:
            lines.append(stripped)
            prev_blank = False
    return "\n".join(lines).strip()

def fix_json_newlines(json_string: str) -> str:
    """Fixes unescaped newlines inside JSON string values using a robust regex."""
    
    def escape_newlines_in_match(match):
        # The match object gives us the entire string literal, including the quotes.
        # We replace literal newlines with their escaped version inside this matched string.
        return match.group(0).replace('\n', '\\n')

    # This regex robustly finds all JSON string literals. It looks for a double quote,
    # followed by any sequence of characters that are not a backslash or a double quote,
    # or any escaped character (e.g., \", \\, \n), and ends with a double quote.
    string_literal_regex = r'"((?:\\.|[^"\\])*)"'
    
    return re.sub(string_literal_regex, escape_newlines_in_match, json_string, flags=re.DOTALL)

def generate_slides_content(text, figures_path=None, max_slides=10, original_filename="document"):
    """
    Generate slide content using Gemini API based on extracted text
    
    Args:
        text (str): Extracted text from the PDF
        figures_path (str, optional): Path to figures metadata JSON
        max_slides (int, optional): Maximum number of slides to generate
        original_filename (str, optional): Original filename (without extension) for naming output files
        
    Returns:
        str: Path to the generated slides JSON file
    """
    # Create output directory if it doesn't exist
    output_dir = Path("slides")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Use the original filename for consistent naming
    base_output_filename = f"{original_filename}_slides_plan"
    
    # Prepare the figures prompt injection if figures are available
    figures_prompt_injection = ""
    if figures_path:
        try:
            with open(figures_path, 'r', encoding='utf-8') as f:
                figures_data = json.load(f)
            
            figures_list_str = ""
            for i, fig in enumerate(figures_data):
                title = fig.get('title', f'Figure {i+1}')
                caption = fig.get('caption', 'No caption available.')
                # The markdown_path will be created by the orchestrator script
                raw_path = fig.get('markdown_path', '')
                # Make the path relative to the location of deck.md (slides/)
                path = os.path.relpath(raw_path, start="slides") if raw_path else ''
                figures_list_str += f"- Figure {i+1}:\n  - Title: {title}\n  - Caption: {caption}\n  - Markdown Path: {path}\n"

            if figures_list_str:
                figures_prompt_injection = f"""\n\n--- AVAILABLE FIGURES ---
You have been provided with a list of figures. Where relevant, you MUST embed these figures into the slide content using their provided Markdown paths (e.g., `![{title}]({path})`).

{figures_list_str}
"""
        except Exception as e:
            print(f"Warning: Could not process figures metadata: {e}")
    
    # Define prompts
    system_prompt = """You are an AI assistant role-playing as a graduate student in a lab meeting, explaining an interesting paper to your peers.
Your tone should be conversational, insightful, and slightly informal. Refer to the paper's authors as 'the authors' or 'the paper,' not 'we'.

Your task is to create a JSON object that represents the slide deck. The JSON object should be a list of slides.
Each slide should have a "slide number", a "title", a "content" field, and an "audio" field.
The "content" field should contain the text for the slide body as a single string, formatted in Markdown.
The "audio" field should contain the narration script for the slide, matching your persona.

IMPORTANT: The output MUST be a single, valid JSON object. Ensure that all strings are properly escaped. For example, use \n for newlines within the content and audio strings, and escape any double quotes. Do not add any extra text or formatting outside of the JSON object itself. The entire response should be parseable by a standard JSON parser."""

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

--- TEXT TO CONVERT ---
{text}

--- END OF TEXT ---
Remember to include the figures in your response where appropriate."""
    
    # Compact whitespace in prompts to save tokens
    compacted_system_prompt = compact_whitespace(system_prompt)
    compacted_user_prompt = compact_whitespace(user_prompt)
    
    try:
        # Call the LLM to generate the slide content
        print("Sending content to the language model for processing...")
        llm_response_str = call_llm(compacted_system_prompt, compacted_user_prompt)
        
        # Parse the JSON response, fixing any unescaped newlines first
        fixed_llm_response = fix_json_newlines(llm_response_str)
        slides_data = json.loads(fixed_llm_response)
        
        # Save the slides data to a JSON file
        json_output_path = output_dir / f"{base_output_filename}.json"
        with open(json_output_path, "w", encoding="utf-8") as f:
            json.dump(slides_data, f, indent=2)
            
        return str(json_output_path)
    except Exception as e:
        raise Exception(f"Error generating slide content: {str(e)}")
