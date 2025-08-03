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

def remove_stop_words(text):
    """
    Remove common stop words and clean text for similarity comparison
    """
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
        'may', 'might', 'must', 'can', 'to', 'of', 'in', 'on', 'at', 'by', 'for',
        'with', 'without', 'through', 'during', 'before', 'after', 'above', 'below',
        'up', 'down', 'out', 'off', 'over', 'under', 'again', 'further', 'then',
        'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both',
        'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
        'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'now', 'and',
        'but', 'or', 'as', 'if', 'because', 'while', 'this', 'that', 'these', 'those'
    }
    
    # Convert to lowercase and split into words
    words = text.lower().split()
    
    # Remove stop words and clean up
    meaningful_words = []
    for word in words:
        # Remove punctuation and special characters
        clean_word = ''.join(c for c in word if c.isalnum()).strip()
        if clean_word and clean_word not in stop_words and len(clean_word) > 2:
            meaningful_words.append(clean_word)
    
    return meaningful_words

def calculate_text_similarity(text1, text2):
    """
    Calculate similarity between two texts based on common meaningful words
    """
    words1 = set(remove_stop_words(text1))
    words2 = set(remove_stop_words(text2))
    
    if not words1 or not words2:
        return 0
    
    # Calculate Jaccard similarity (intersection over union)
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    if union == 0:
        return 0
    
    jaccard_score = intersection / union
    
    # Also calculate overlap score (common words / total words in slide)
    overlap_score = intersection / len(words1) if words1 else 0
    
    # Return weighted combination
    return (jaccard_score * 0.6) + (overlap_score * 0.4)

def match_figures_to_slides(slides, figures_data):
    """
    Intelligently match figures to slides based on text similarity with figure captions
    """
    if not figures_data or not slides:
        return slides
    
    print(f"🔄 FALLBACK: Matching {len(figures_data)} figures to {len(slides)} slides using text similarity...")
    
    for slide_idx, slide in enumerate(slides):
        content = slide.get('content', '')
        audio = slide.get('audio', '')
        title = slide.get('title', '')
        
        # Combine all slide text for analysis
        slide_text = f"{title} {content} {audio}"
        
        print(f"📝 FALLBACK: Processing slide {slide_idx + 1}: '{title[:50]}...'")
        
        # Score each figure based on text similarity
        figure_scores = {}
        for fig_idx, figure in enumerate(figures_data):
            fig_title = figure.get('title', '')
            fig_caption = figure.get('caption', '')
            
            # Combine figure text
            figure_text = f"{fig_title} {fig_caption}"
            
            # Calculate similarity score
            similarity = calculate_text_similarity(slide_text, figure_text)
            
            # Bonus for explicit figure mentions
            if f"figure {fig_idx + 1}" in slide_text.lower() or f"fig {fig_idx + 1}" in slide_text.lower():
                similarity += 0.5
            
            figure_scores[fig_idx + 1] = similarity
            print(f"  🔍 Figure {fig_idx + 1} similarity: {similarity:.3f}")
        
        # Add the most relevant figure to this slide
        if figure_scores:
            # Get the figure with highest similarity
            best_fig_idx = max(figure_scores.items(), key=lambda x: x[1])
            fig_idx, score = best_fig_idx
            
            # Only add if similarity is reasonable (> 0.1)
            if score > 0.1:
                figure = figures_data[fig_idx - 1]
                fig_title = figure.get('title', f'Figure {fig_idx}')
                path = figure.get('markdown_path', '')
                
                print(f"✅ FALLBACK: Adding Figure {fig_idx} (score: {score:.3f}) to slide {slide_idx + 1}")
                print(f"   📁 Path: {path}")
                
                if path:
                    # Use absolute path directly since Marp will run with --allow-local-files
                    figure_markdown = f"![{fig_title}]({path})"
                    
                    # Inject figure into content
                    current_content = slide.get('content', '')
                    slide['content'] = current_content + '\n\n' + figure_markdown
                    print(f"   ✅ Added figure to slide content")
            else:
                print(f"   ❌ No figures with sufficient similarity (best: {score:.3f})")
    
    return slides

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
    figures_data = None
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
                # Use absolute path directly - Marp can handle it with --allow-local-files
                if raw_path and raw_path.startswith('/'):
                    # Already absolute path
                    path = raw_path
                elif raw_path:
                    # Convert relative path to absolute
                    import os
                    path = os.path.abspath(raw_path)
                else:
                    path = ''
                figures_list_str += f"- Figure {i+1}:\n  - Title: {title}\n  - Caption: {caption}\n  - Markdown Path: {path}\n"

            if figures_list_str:
                figures_prompt_injection = f"""\n\n=== MANDATORY FIGURE EMBEDDING ===
🚨 CRITICAL REQUIREMENT: You MUST include figures using markdown syntax in EVERY slide's content field!

❌ WRONG - Do NOT write: "Figure 1 shows..." or "as seen in Figure 1"
✅ CORRECT - You MUST write: ![Figure 1: Title](path)

🔥 REQUIREMENT: Each slide's "content" field MUST contain at least ONE figure using this EXACT syntax:
![Title](path)

📋 AVAILABLE FIGURES (copy these EXACTLY):
{figures_list_str}

💡 EXAMPLE of REQUIRED content field format:
```
"content": "* Key finding about SomArchon\\n* Novel voltage indicator\\n\\n![USE_EXACT_PATHS_FROM_ABOVE](COPY_PATHS_EXACTLY_FROM_FIGURE_LIST)"
```

⚠️  FAILURE TO INCLUDE FIGURES WILL RESULT IN REJECTION!
⚠️  COPY THE PATHS EXACTLY - DO NOT MODIFY THEM!
⚠️  FIGURES MUST BE IN THE "content" FIELD, NOT IN "audio"!

🎯 Your JSON response will be checked for figure markdown syntax. If missing, it will fail validation.
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

CRITICAL RULE: The "content" field must be EXTREMELY SHORT - maximum 2-3 bullet points, each under 30 words. This is visual text only. The figures should be the main focus, not text.
The "audio" field should contain the full, detailed narration for the slide, matching your persona.

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
- "title": A concise title for the slide (maximum 8 words).
- "content": CRITICAL - Keep this ULTRA MINIMAL! Maximum 2-3 short bullet points, each under 30 words. Think of this as slide headlines only. The audience should focus on figures, not read paragraphs.
- "audio": This should contain the full, detailed narration for the slide, suitable for text-to-speech. Maximize information transfer here.

CONTENT EXAMPLES (DO NOT exceed this length):
❌ TOO LONG: "* SomaArchon enables high-fidelity voltage imaging in brain slices, demonstrating improved sensitivity and SNR compared to existing voltage indicators like Archon1."
✅ PERFECT: "* High-fidelity voltage imaging in brain slices"
✅ PERFECT: "* Improved sensitivity vs existing indicators"

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
            print(f"  🔄 Calling Gemma3n for chunk {i+1}...")
            chunk_slides_list = call_ollama_llm(compacted_system_prompt, compacted_user_prompt)
            print(f"  📋 Gemma3n returned: {type(chunk_slides_list)} with {len(chunk_slides_list) if chunk_slides_list else 0} items")
            
            if chunk_slides_list:
                # Add slides from this chunk to our collection
                for slide in chunk_slides_list:
                    # Ensure slide number is correctly set
                    slide["slide number"] = slide_counter
                    all_slides.append(slide)
                    slide_counter += 1
                    remaining_slides -= 1
                    
                print(f"  ✅ Generated {len(chunk_slides_list)} slides from chunk {i+1}")
            else:
                print(f"  ❌ Warning: No slides generated from chunk {i+1}")
                # This might cause the overall process to fail
                print(f"  📊 chunk_slides_list value: {chunk_slides_list}")
                print(f"  📊 Type: {type(chunk_slides_list)}")
                return None  # Explicit failure to help debug
                
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
    
    # CHECK: Did Gemma3n include VALID figures in the slides?
    valid_figures_found = False
    if figures_data and all_slides:
        # Get list of valid figure paths for validation
        valid_paths = {fig.get('markdown_path', '') for fig in figures_data}
        
        for slide in all_slides:
            content = slide.get('content', '')
            # Check if slide contains figure markdown
            if '![' in content and '](' in content:
                # Extract the figure path from the markdown
                figure_matches = re.findall(r'!\[.*?\]\((.*?)\)', content)
                for path in figure_matches:
                    # Check if the path is one of our valid paths
                    if path in valid_paths:
                        valid_figures_found = True
                        break
                    else:
                        print(f"⚠️  Found INVALID figure path in slide: {path}")
                if valid_figures_found:
                    break
        
        if valid_figures_found:
            print("✅ SUCCESS: Gemma3n included VALID figures in slides!")
        else:
            print("❌ FALLBACK: Gemma3n didn't include valid figures (may have fake paths). Using intelligent matching...")
            # Clean up any invalid figure references before applying fallback
            for slide in all_slides:
                content = slide.get('content', '')
                # Remove any existing invalid figure references
                content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
                slide['content'] = content.strip()
            
            all_slides = match_figures_to_slides(all_slides, figures_data)
            print("✅ Figures added via intelligent content matching")
    
    try:
        # Save the slides data to the final JSON file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_slides, f, indent=2)
            
        print(f"Generated {len(all_slides)} slides total with figures")
        return str(output_path)
        
    except Exception as e:
        raise Exception(f"Error saving slide content: {str(e)}")
