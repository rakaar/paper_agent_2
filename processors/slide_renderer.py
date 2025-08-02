import os
import sys
import subprocess
from pathlib import Path

def render_slides(marp_md_path, frames_dir=None):
    """
    Render Marp markdown as PNG images using marp-cli
    
    Args:
        marp_md_path (str): Path to the Marp markdown file
        
    Returns:
        str: Path to the directory containing rendered PNG frames
    """
    # Determine output directory for frames
    if frames_dir is None:
        frames_dir = Path("slides") / "frames"
    else:
        frames_dir = Path(frames_dir)
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
        
        print(f"Running Marp command: {' '.join(cmd)}")
        
        # Execute the command and capture output
        result = subprocess.run(
            cmd, 
            check=False,  # Don't raise immediately, we'll handle it
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            error_details = []
            error_details.append(f"Marp command failed with exit code {result.returncode}")
            error_details.append(f"Command: {' '.join(cmd)}")
            
            if result.stdout:
                error_details.append(f"STDOUT: {result.stdout.strip()}")
            
            if result.stderr:
                error_details.append(f"STDERR: {result.stderr.strip()}")
            
            # Check for common issues and suggest solutions
            stderr_lower = result.stderr.lower() if result.stderr else ""
            stdout_lower = result.stdout.lower() if result.stdout else ""
            
            if "no such file or directory" in stderr_lower or "command not found" in stderr_lower:
                if "marp" in stderr_lower:
                    error_details.append("SOLUTION: Install Marp CLI with: npm i -g @marp-team/marp-cli")
                elif "npx" in stderr_lower:
                    error_details.append("SOLUTION: Install Node.js and npm first, then install Marp CLI")
            elif "permission denied" in stderr_lower:
                error_details.append("SOLUTION: Check file permissions or run with appropriate privileges")
            elif "enoent" in stderr_lower:
                error_details.append("SOLUTION: Check that the input markdown file exists and is accessible")
            elif "syntax error" in stderr_lower or "parse" in stderr_lower:
                error_details.append("SOLUTION: Check the Marp markdown syntax in the slides file")
            elif "browser" in stderr_lower or "chromium" in stderr_lower:
                error_details.append("SOLUTION: Install a browser (Chromium/Chrome) for Marp rendering")
                error_details.append("  - Ubuntu: sudo apt install chromium-browser")
                error_details.append("  - Or use --chrome-path flag to specify browser location")
            elif "out of memory" in stderr_lower or "killed" in stderr_lower:
                error_details.append("SOLUTION: Insufficient memory. Try reducing image scale or slide count")
            
            raise Exception("Marp slide rendering failed:\n" + "\n".join(error_details))
        
        print("Marp rendering completed successfully")
        
        # Verify that frames were generated
        png_files = list(frames_dir.glob("deck.*.png"))
        if not png_files:
            raise Exception(
                f"Marp command succeeded but no PNG frames were generated in {frames_dir}\n"
                f"Expected files like: deck.001.png, deck.002.png, etc.\n"
                f"Directory contents: {list(frames_dir.glob('*'))}"
            )
        
        print(f"Successfully generated {len(png_files)} slide images")
        return str(frames_dir)
        
    except subprocess.CalledProcessError as e:
        # This shouldn't happen anymore since we use check=False
        raise Exception(f"Subprocess error: {str(e)}")
    except Exception as e:
        # Re-raise with more context if it's our custom exception
        if "Marp slide rendering failed" in str(e):
            raise e
        else:
            raise Exception(f"Error rendering slides: {str(e)}")
