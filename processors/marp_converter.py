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
        # Check if the JSON file exists
        if not os.path.exists(json_file_path):
            raise FileNotFoundError(f"JSON file not found: {json_file_path}")
        
        # Check if figures metadata exists if provided
        if figures_metadata_path and not os.path.exists(figures_metadata_path):
            raise FileNotFoundError(f"Figures metadata file not found: {figures_metadata_path}")
        
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
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Verify that the markdown file was created
        if not os.path.exists(marp_md_path):
            raise FileNotFoundError(f"Marp markdown file not found at {marp_md_path}")
        
        return str(marp_md_path)
    
    except subprocess.CalledProcessError as e:
        error_msg = f"Error converting JSON to Marp markdown: Command {' '.join(cmd)} returned non-zero exit status {e.returncode}."
        if e.stderr:
            error_msg += f"\nSTDERR: {e.stderr}"
        if e.stdout:
            error_msg += f"\nSTDOUT: {e.stdout}"
        raise Exception(error_msg)
    except Exception as e:
        raise Exception(f"Error in Marp conversion: {str(e)}")
