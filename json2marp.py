#!/usr/bin/env python3
"""
Convert Gemini-style JSON → Marp Markdown with MathJax enabled.
Usage:  python json2marp.py llm_slides.json  -o slides/deck.md
"""
import argparse, json, pathlib, textwrap
from tqdm import tqdm

FRONT_MATTER = """---
marp: true
math: mathjax
paginate: true
theme: gaia
---"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file", type=pathlib.Path, help="Path to the LLM JSON output file.")
    ap.add_argument("-o", "--out", type=pathlib.Path, default="slides/deck.md", help="Output Marp Markdown file.")
    args = ap.parse_args()

    slides = json.loads(args.json_file.read_text())
    
    def get_slide_num(s):
        return s.get("slide_number") or s.get("slide number")

    sorted_slides = sorted(slides, key=lambda x: get_slide_num(x) if get_slide_num(x) is not None else float('inf'))

    slide_markdowns = []
    for s in sorted_slides:
        slide_num = get_slide_num(s) or "N/A"
        title = s.get("title", f"Untitled Slide {slide_num}")
        content = s.get("content", "No content provided.")

        if isinstance(content, list):
            content = "\n".join(content)

        slide_md = f"# {title}\n\n{content}"
        slide_markdowns.append(slide_md)

    # Join the individual slide markdowns with the separator
    all_slides_md = "\n\n---\n\n".join(slide_markdowns)
    
    # Prepend the front matter, separated by a comment, to the combined slides
    final_md = f"{FRONT_MATTER}\n\n<!-- -->\n\n{all_slides_md}"


    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(final_md)
    print("✅ Wrote", args.out)

if __name__ == "__main__":
    main()
