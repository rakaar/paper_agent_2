import re

INPUT_FILE = "slides/full_llm_prompt.txt"
OUTPUT_FILE = "slides/full_llm_prompt.cleaned.txt"

def clean_prompt(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned_lines = []
    buffer = []
    for line in lines:
        stripped = line.strip()
        # Replace common Unicode space characters with normal space
        stripped = stripped.replace('\u00A0', ' ').replace('\u2002', ' ').replace('\u2003', ' ').replace('\u2009', ' ')
        # Normalize ALL whitespace (spaces, tabs, unicode, etc.) to single space
        stripped = re.sub(r'\s+', ' ', stripped)
        stripped = stripped.strip()
        # Debug: print lines with suspicious spacing
        if re.search(r' {3,}', stripped):
            print(f"DEBUG: Unusual spacing: {repr(stripped)}")
        # Merge single-word/character lines with buffer
        if len(stripped) <= 2 and stripped and not re.match(r'^[-=]+$', stripped):
            buffer.append(stripped)
            continue
        if buffer:
            cleaned_lines.append(' '.join(buffer))
            buffer = []
        # Collapse multiple empty lines
        if stripped == '' and (not cleaned_lines or cleaned_lines[-1] == ''):
            continue
        # Remove lines that are only markdown section headers
        if re.match(r'^={3,}|^-{3,}|^\*{3,}$', stripped):
            continue
        # Compact figure markdown/caption blocks
        if stripped.startswith('- Figure'):
            # Try to merge next lines into one
            cleaned_lines.append(stripped)
            continue
        cleaned_lines.append(stripped)
    if buffer:
        cleaned_lines.append(' '.join(buffer))

    # Merge consecutive short lines into paragraphs
    output = []
    para = []
    for line in cleaned_lines:
        if len(line) < 40 and not line.startswith('-') and line:
            para.append(line)
        else:
            if para:
                output.append(' '.join(para))
                para = []
            output.append(line)
    if para:
        output.append(' '.join(para))

    # Remove excessive empty lines
    final = []
    for line in output:
        if line == '' and (not final or final[-1] == ''):
            continue
        final.append(line)

    with open(output_path, 'w', encoding='utf-8') as f:
        for line in final:
            f.write(line + '\n')

if __name__ == "__main__":
    clean_prompt(INPUT_FILE, OUTPUT_FILE)
