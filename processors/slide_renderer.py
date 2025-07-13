import os
import sys
import subprocess
from pathlib import Path

def render_slides(marp_md_path):
    """
    Render Marp markdown as PNG images using marp-cli
    
    Args:
        marp_md_path (str): Path to the Marp markdown file
        
    Returns:
        str: Path to the directory containing rendered PNG frames
    """
    # Create output directory for frames
    frames_dir = Path("slides") / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    # Marp CLI needs a dummy file path in the target directory for image sequence output
    frames_output_path_template = frames_dir / "deck.png"
    
    try:
        # Check if marp-cli is installed
        try:
            subprocess.run(["npx", "marp", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            raise RuntimeError("marp-cli not found. Please install it with 'npm i -g @marp-team/marp-cli'")
        
        # Render Marp markdown to PNG frames
        cmd = [
            "npx", "marp", 
            str(marp_md_path),
            "--images", "png",
            "--image-scale", "2",
            "--allow-local-files",
            # Provide a dummy file path; marp-cli will use its basename for the sequence
            "--output", str(frames_output_path_template)
        ]
        
        # Execute the command
        subprocess.run(cmd, check=True)
        
        # Verify that frames were generated
        png_files = list(frames_dir.glob("deck.*.png"))
        if not png_files:
            raise FileNotFoundError(f"No PNG frames were generated in {frames_dir}")
        
        return str(frames_dir)
        
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error rendering Marp markdown to PNGs: {str(e)}")
    except Exception as e:
        raise Exception(f"Error rendering slides: {str(e)}")
