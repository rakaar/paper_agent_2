import os
import sys
import subprocess
import json
from pathlib import Path

def convert_to_marp(json_file_path, figures_metadata_path=None):
    """
    Convert slide plan JSON to Marp markdown using the existing json2marp.py script
    
    Args:
        json_file_path (str): Path to the slides plan JSON file
        figures_metadata_path (str, optional): Path to figures metadata. Defaults to None.

    Returns:
        str: Path to the generated Marp markdown file
    """
    # Define the output path for the Marp markdown
    output_dir = Path("slides")
    output_dir.mkdir(parents=True, exist_ok=True)
    marp_md_path = output_dir / "deck.md"
    
    try:
        # Call the json2marp.py script to convert JSON to Marp markdown
        cmd = [
            sys.executable,
            "json2marp.py",
            str(json_file_path),
            "--out", str(marp_md_path)
        ]

        if figures_metadata_path:
            cmd.extend(["--figures-path", str(figures_metadata_path)])
        
        # Execute the command
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Verify that the markdown file was created
        if not os.path.exists(marp_md_path):
            raise FileNotFoundError(f"Marp markdown file not found at {marp_md_path}")
        
        return str(marp_md_path)
    
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error converting JSON to Marp markdown: {str(e)}")
    except Exception as e:
        raise Exception(f"Error in Marp conversion: {str(e)}")
