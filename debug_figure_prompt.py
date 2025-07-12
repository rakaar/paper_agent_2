import os
import json
from pdf2json import call_llm

def debug_llm_figure_prompt():
    """Sends a minimal, hardcoded prompt to the LLM to test figure embedding."""
    print("--- Running Minimal LLM Figure Test ---")

    system_prompt = """You are a helpful assistant. Create a JSON object representing a single slide. The slide must have 'title' and 'content' keys. The 'content' must be a single Markdown string."""

    figure_info = """- Figure 1:\n  - Title: Test Figure\n  - Caption: This is a test caption.\n  - Markdown Path: figures/figure-1.png\n"""

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
    # Ensure the API key is set, similar to the main script
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set.")
    else:
        debug_llm_figure_prompt()
