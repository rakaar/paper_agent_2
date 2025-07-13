import os
import sys
import json
import subprocess
from pathlib import Path

def extract_figures(pdf_path, output_dir):
    """
    Extract figures from a PDF using the extract_images_llm.py script
    
    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Directory to store extracted figures
        
    Returns:
        str: Path to the figures metadata JSON file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Run the extract_images_llm.py script to extract figures
    try:
        cmd = [
            sys.executable,
            "extract_images_llm.py",
            pdf_path,
            "--output_dir", output_dir
        ]
        
        # Execute the command
        subprocess.run(cmd, check=True)
        
        # The figures metadata should be saved in the output directory
        figures_metadata_path = os.path.join(output_dir, "figures_metadata.json")
        
        # Verify that the metadata file exists
        if not os.path.exists(figures_metadata_path):
            raise FileNotFoundError(f"Figures metadata file not found at {figures_metadata_path}")
        
        # Update the markdown_path for each figure to include the full path
        with open(figures_metadata_path, 'r') as f:
            figures_data = json.load(f)
        
        for figure in figures_data:
            png_filename = figure.get('png_filename')
            if png_filename:
                full_path = os.path.join(output_dir, png_filename)
                figure['markdown_path'] = full_path
        
        # Write the updated metadata back to the file
        with open(figures_metadata_path, 'w') as f:
            json.dump(figures_data, f, indent=2)
        
        return figures_metadata_path
        
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error running extract_images_llm.py: {str(e)}")
    except Exception as e:
        raise Exception(f"Error extracting figures: {str(e)}")
