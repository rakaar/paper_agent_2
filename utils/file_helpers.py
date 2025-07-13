import os
import tempfile
from pathlib import Path

def save_uploaded_file(uploaded_file, target_dir):
    """
    Save an uploaded file to the target directory
    
    Args:
        uploaded_file (UploadedFile): The file uploaded through Streamlit
        target_dir (str): Directory to save the file in
        
    Returns:
        str: Path to the saved file
    """
    # Create target directory if it doesn't exist
    os.makedirs(target_dir, exist_ok=True)
    
    # Generate a path for the saved file
    file_path = os.path.join(target_dir, uploaded_file.name)
    
    # Write the file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path

def clean_temp_files(temp_dir):
    """
    Clean up temporary files
    
    Args:
        temp_dir (str): Directory with temporary files to clean up
    """
    import shutil
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Error cleaning up temp files: {e}")
