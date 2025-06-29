#!/usr/bin/env python3
"""
Convert Gemini-style JSON → Marp Markdown with MathJax enabled.
Usage:  python json2marp.py llm_slides.json  -o slides/deck.md
"""
import argparse, json, pathlib, textwrap
from tqdm import tqdm

FRONT_MATTER = textwrap.dedent("""
    ---
    marp: true
    math: mathjax        # guarantee MathJax even if Marp’s default changes
    paginate: true
    theme: gaia          # or default / uncover / custom CSS
    ---
""")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file", type=pathlib.Path, help="Path to the LLM JSON output file.")
    ap.add_argument("-o", "--out", type=pathlib.Path, default="slides/deck.md", help="Output Marp Markdown file.")
    args = ap.parse_args()

    slides = json.loads(args.json_file.read_text())
    md = [FRONT_MATTER]

    # Sort slides, handling missing 'slide number' gracefully
    sorted_slides = sorted(slides, key=lambda x: x.get("slide number", float('inf')))

    for s in sorted_slides:
        slide_num = s.get("slide number", "N/A")
        title = s.get("title", f"Untitled Slide {slide_num}")
        content = s.get("content", "No content provided.")
        audio = s.get("audio", "No audio provided.")

        if "slide number" not in s:
            print(f"Warning: Slide entry missing 'slide number' key: {s}")
        if "title" not in s:
            print(f"Warning: Slide {slide_num} entry missing 'title' key.")
        if "content" not in s:
            print(f"Warning: Slide {slide_num} entry missing 'content' key.")
        if "audio" not in s:
            print(f"Warning: Slide {slide_num} entry missing 'audio' key.")

        if isinstance(content, list):
            content = "\n".join(content) # Join list elements into a string

        md.append(f"# {title}\n")
        md.append(content)      # keep $$…$$ math untouched
        md.append("\n---\n")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(md))
    print("✅ Wrote", args.out)

if __name__ == "__main__":
    main()
