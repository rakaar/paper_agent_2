#!/usr/bin/env python3
"""
Convert Gemini-style JSON → Marp Markdown with MathJax enabled.
Usage:  python json2marp.py llm_slides.json  -o slides/deck.md
"""
import argparse, json, pathlib, sys, textwrap
from tqdm import tqdm

FRONT_MATTER = """---
marp: true
math: mathjax
paginate: true
theme: gaia
style: |
  /* Global slide tweaks */
  section {
    padding-top: 0.2em;
  }
  section h1 {
    font-size: 1.6em;
    line-height: 1.2;
  }
  /* Ensure images fit within slide without being cut */
  section img {
    max-height: 45vh;
    max-width: 80%;
    height: auto;
    object-fit: contain;
    display: block;
    margin: 1em auto;
  }

  /* When slide has an image, shrink heading and body font */
  section.has-image h1 {
    font-size: 1.2em;
  }
  section.has-image h2 {
    font-size: 1.2em;
  }
  section.has-image ul,
  section.has-image p {
    font-size: 0.8em;
  }
---"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file", type=pathlib.Path, help="Path to the LLM JSON output file.")
    ap.add_argument("-o", "--out", type=pathlib.Path, default="slides/deck.md", help="Output Marp Markdown file.")
    ap.add_argument("--figures-path", type=pathlib.Path, default=None, help="Path to the figures metadata JSON file.")
    args = ap.parse_args()

    try:
        data = json.loads(args.json_file.read_text())
        if isinstance(data, dict) and 'slides' in data:
            slides = data['slides']
        else:
            slides = data
        
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

        all_slides_md = "\n\n---\n\n".join(slide_markdowns)
        final_md = f"{FRONT_MATTER}\n\n<!-- -->\n\n{all_slides_md}"

        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(final_md)
        print(f"✅ Wrote {args.out}")

    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in json2marp.py: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
