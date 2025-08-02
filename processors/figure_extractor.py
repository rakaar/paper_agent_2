from .mistral_cache import get_mistral_extractor

def extract_figures(pdf_path, output_dir):
    """
    Extract figures from a PDF using Mistral OCR API
    
    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Directory to store extracted figures
        
    Returns:
        str: Path to the figures metadata JSON file
    """
    try:
        extractor = get_mistral_extractor(pdf_path)
        return extractor.get_figures(output_dir)
    except Exception as e:
        raise Exception(f"Error extracting figures with Mistral: {str(e)}")