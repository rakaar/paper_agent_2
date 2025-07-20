#!/usr/bin/env python3
"""
Test script to verify the JSON structure expected by json2marp.py
"""

import json
import subprocess
import sys
from pathlib import Path

# Create a test JSON structure that matches what json2marp.py expects
test_slides = [
    {
        "slide_number": 1,
        "title": "Test Slide 1",
        "content": "This is the content of the first slide.",
        "audio": "This is the narration for slide 1"
    },
    {
        "slide_number": 2,
        "title": "Test Slide 2", 
        "content": "This is the content of the second slide.\n\n- Point 1\n- Point 2",
        "audio": "This is the narration for slide 2"
    }
]

# Save test JSON
test_json_path = "test_slides.json"
with open(test_json_path, 'w', encoding='utf-8') as f:
    json.dump(test_slides, f, indent=2, ensure_ascii=False)

print(f"Created test JSON file: {test_json_path}")
print("Contents:")
with open(test_json_path, 'r') as f:
    print(f.read())

# Test json2marp.py with this structure
print("\nTesting json2marp.py...")
try:
    result = subprocess.run([
        sys.executable,
        "json2marp.py",
        test_json_path,
        "--out", "test_deck.md"
    ], capture_output=True, text=True, check=True)
    
    print("✅ json2marp.py ran successfully!")
    print("Generated Markdown:")
    with open("test_deck.md", 'r') as f:
        print(f.read()[:500] + "..." if len(f.read()) > 500 else f.read())
        
except subprocess.CalledProcessError as e:
    print(f"❌ json2marp.py failed:")
    print(f"Return code: {e.returncode}")
    print(f"Stdout: {e.stdout}")
    print(f"Stderr: {e.stderr}")

# Clean up
Path(test_json_path).unlink(missing_ok=True)
Path("test_deck.md").unlink(missing_ok=True)
