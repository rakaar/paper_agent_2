import os
import json
from pdf2json import call_llm

import argparse

def debug_llm_figure_prompt(figures_path: str = None):
    """Sends a minimal prompt to the LLM to test figure embedding.

If --figures-path is supplied, it will load the consolidated figures_metadata.json
created by extract_images_llm.py and build the same figure list string that
`txt2slides.py` injects, letting you preview exactly what the slide-generator
will send to Gemini.
"""
    print("--- Running Minimal LLM Figure Test ---")

    system_prompt = """You are a helpful assistant. Create a JSON object representing a single slide. The slide must have 'title' and 'content' keys. The 'content' must be a single Markdown string."""

    # Build figure info string
    if figures_path:
        try:
            with open(figures_path, 'r', encoding='utf-8') as f:
                figs = json.load(f)
            figure_info_lines = []
            for idx, fig in enumerate(figs, start=1):
                figure_info_lines.append(
                    f"- Figure {idx}:\n  - Title: {fig.get('title','')}\n  - Caption: {fig.get('caption','')}\n  - Markdown Path: {fig.get('markdown_path','')}\n")
            figure_info = "".join(figure_info_lines)
        except Exception as e:
            print(f"Could not load figures from {figures_path}: {e}. Falling back to dummy figure info.")
            figure_info = "- Figure 1:\n  - Title: Test Figure\n  - Caption: This is a test caption.\n  - Markdown Path: figures/figure-1.png\n"
    else:
        figure_info = "- Figure 1:\n  - Title: Test Figure\n  - Caption: This is a test caption.\n  - Markdown Path: figures/figure-1.png\n"

    figures_prompt_injection = f"""\n\n--- AVAILABLE FIGURES ---\nYou MUST embed the following figure into the slide content using its Markdown path: `![title](path)`\n\n{figure_info}"""

    user_prompt = f"""Create one slide about neural networks. {figures_prompt_injection}"""

    print("\n--- System Prompt ---")
    print(system_prompt)
    print("\n--- User Prompt ---")
    print(user_prompt)

    try:
        llm_response_str = call_llm(system_prompt, user_prompt)
        print("\n--- Raw LLM Response ---")
        print(llm_response_str)

    except Exception as e:
        print(f"\n--- ERROR ---")
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--figures-path", type=str, help="Path to figures_metadata.json produced by extraction script.")
    args = ap.parse_args()

    # Ensure the API key is set, similar to the main script
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set.")
    else:
        debug_llm_figure_prompt(args.figures_path)
