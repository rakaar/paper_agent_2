import fitz  # PyMuPDF
import os

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file using PyMuPDF (fitz)
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text from the PDF
    """
    try:
        doc = fitz.open(pdf_path)
        text = ""
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text += page.get_text()
        
        doc.close()
        return text
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")
