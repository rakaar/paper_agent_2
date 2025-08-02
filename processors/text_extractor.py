from .mistral_cache import get_mistral_extractor

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file using Mistral OCR API
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text from the PDF in markdown format
    """
    try:
        extractor = get_mistral_extractor(pdf_path)
        return extractor.get_text()
    except Exception as e:
        raise Exception(f"Error extracting text with Mistral: {str(e)}")