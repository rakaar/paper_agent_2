import os
import json
import sys
from pathlib import Path

sys.path.append(os.path.abspath('.'))  # Add project root to path
from pdf2json import call_ollama_llm
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

def split_text_into_chunks(text: str, max_chunk_size: int = 4000) -> list:
    """
    Split text into smaller chunks suitable for Gemma3n's limited context length.
    
    Args:
        text (str): The full text to split
        max_chunk_size (int): Maximum characters per chunk
        
    Returns:
        list: List of text chunks
    """
    # Split by paragraphs first to maintain coherence
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed limit, save current chunk
        if len(current_chunk) + len(paragraph) + 2 > max_chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph
        else:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
    
    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def generate_slides_content(text, figures_path=None, max_slides=10, output_dir=".", original_filename="document"):
    """
    Generate slide content using Gemma3n API with page-by-page processing based on extracted text
    
    Args:
        text (str): Extracted text from the PDF
        figures_path (str, optional): Path to figures metadata JSON
        max_slides (int, optional): Maximum number of slides to generate
        output_dir (str, optional): Directory to save the output JSON file
        original_filename (str, optional): Original filename (without extension) for naming output files
        
    Returns:
        str: Path to the generated slides JSON file
    """
    # Define output path using the provided output_dir
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    output_filename = f"{original_filename}_slides_plan.json"
    output_path = output_dir_path / output_filename
    
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
    
    # Split text into chunks for page-by-page processing due to Gemma3n's limited context
    text_chunks = split_text_into_chunks(text, max_chunk_size=4000)
    print(f"Split text into {len(text_chunks)} chunks for processing...")
    
    # Calculate slides per chunk
    slides_per_chunk = max(1, max_slides // len(text_chunks))
    remaining_slides = max_slides
    
    all_slides = []
    slide_counter = 1
    
    # Define system prompt for chunk processing
    system_prompt = """You are an AI assistant role-playing as a graduate student in a lab meeting, explaining an interesting paper to your peers.
Your tone should be conversational, insightful, and slightly informal. Refer to the paper's authors as 'the authors' or 'the paper,' not 'we'.

Your task is to create slides from a portion of a research paper. Return ONLY a JSON object containing a "slides" array.
Each slide should have a "slide number", a "title", a "content" field, and an "audio" field.
The "content" field should contain the text for the slide body as a single string, formatted in Markdown.
The "audio" field should contain the narration script for the slide, matching your persona.

IMPORTANT: The output MUST be a valid JSON object with a "slides" key containing an array. Do not add any extra text outside of the JSON object."""
    
    # Process each chunk
    for i, chunk in enumerate(text_chunks):
        # Calculate how many slides for this chunk
        if i == len(text_chunks) - 1:  # Last chunk gets remaining slides
            chunk_slides = remaining_slides
        else:
            chunk_slides = min(slides_per_chunk, remaining_slides)
        
        if chunk_slides <= 0:
            break
            
        user_prompt = f"""Create {chunk_slides} slides from this text chunk. Each slide must have these exact keys: "slide number", "title", "content", and "audio".

Start slide numbering from {slide_counter}.

- "slide number": An integer for the slide order.
- "title": A concise title for the slide.
- "content": Keep this extremely minimal - 3-4 bullets or brief paragraph. This is for on-screen text only.
- "audio": This should contain the full, detailed narration for the slide, suitable for text-to-speech. Maximize information transfer here.

{figures_prompt_injection}

--- TEXT CHUNK ---
{chunk}

--- END OF TEXT CHUNK ---
Return only the JSON object with the "slides" array."""
        
        # Compact whitespace in prompts to save tokens
        compacted_system_prompt = compact_whitespace(system_prompt)
        compacted_user_prompt = compact_whitespace(user_prompt)
        
        try:
            print(f"Processing chunk {i+1}/{len(text_chunks)} (requesting {chunk_slides} slides)...")
            
            # Call Gemma3n for this chunk
            chunk_slides_list = call_ollama_llm(compacted_system_prompt, compacted_user_prompt)
            
            if chunk_slides_list:
                # Add slides from this chunk to our collection
                for slide in chunk_slides_list:
                    # Ensure slide number is correctly set
                    slide["slide number"] = slide_counter
                    all_slides.append(slide)
                    slide_counter += 1
                    remaining_slides -= 1
                    
                print(f"  Generated {len(chunk_slides_list)} slides from chunk {i+1}")
            else:
                print(f"  Warning: No slides generated from chunk {i+1}")
                
        except Exception as e:
            print(f"  Error processing chunk {i+1}: {e}")
            continue
    
    # If we don't have enough slides, create a summary slide
    if len(all_slides) < max_slides and text_chunks:
        summary_prompt = f"""Create 1 summary slide that wraps up the key findings of this paper.
        
Start slide numbering from {slide_counter}.

Return only the JSON object with the "slides" array containing one slide with keys: "slide number", "title", "content", and "audio".

Based on the full paper context, create a conclusive slide."""
        
        try:
            summary_slides = call_ollama_llm(compact_whitespace(system_prompt), compact_whitespace(summary_prompt))
            if summary_slides:
                for slide in summary_slides:
                    slide["slide number"] = slide_counter
                    all_slides.append(slide)
                    slide_counter += 1
        except Exception as e:
            print(f"  Error creating summary slide: {e}")
    
    # Trim to exact number of requested slides
    if len(all_slides) > max_slides:
        all_slides = all_slides[:max_slides]
    
    try:
        # Save the slides data to the final JSON file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_slides, f, indent=2)
            
        print(f"Generated {len(all_slides)} slides total")
        return str(output_path)
        
    except Exception as e:
        raise Exception(f"Error saving slide content: {str(e)}")
