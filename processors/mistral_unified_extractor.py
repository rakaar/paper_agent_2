import os
import sys
import json
import subprocess
from pathlib import Path
import re

# Import configuration
try:
    from mistral_config import MISTRAL_API_KEY, CLEANUP_TEMP_FILES
except ImportError:
    # Fallback values
    MISTRAL_API_KEY = None
    CLEANUP_TEMP_FILES = True

class MistralExtractor:
    """
    Unified Mistral OCR extractor that processes PDF once and provides both text and figures
    """
    
    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)
        self.pdf_name = self.pdf_path.stem
        self.mistral_output_dir = None
        self.text_content = None
        self.figures_metadata = None
        self._processed = False
    
    def process_pdf(self, temp_dir="temp_mistral_unified"):
        """
        Process PDF with Mistral OCR API once and cache results
        """
        if self._processed:
            return  # Already processed
        
        try:
            self.mistral_output_dir = Path(temp_dir)
            
            # Set up environment for the subprocess
            env = os.environ.copy()
            if MISTRAL_API_KEY:
                env["MISTRAL_API_KEY"] = MISTRAL_API_KEY
            
            cmd = [
                sys.executable,
                "extract_mistral_pdf.py",
                str(self.pdf_path),
                "--out", str(self.mistral_output_dir)
            ]
            
            # Execute the command
            subprocess.run(cmd, check=True, env=env)
            
            # Cache the results
            self._extract_text_content()
            self._extract_figures_metadata()
            
            self._processed = True
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Error running extract_mistral_pdf.py: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing PDF with Mistral: {str(e)}")
    
    def _extract_text_content(self):
        """Extract and combine markdown text from all pages"""
        markdown_dir = self.mistral_output_dir / self.pdf_name / "markdown"
        
        if not markdown_dir.exists():
            raise FileNotFoundError(f"Markdown directory not found: {markdown_dir}")
        
        # Get all markdown files sorted by page number
        markdown_files = sorted(markdown_dir.glob("*.md"))
        
        if not markdown_files:
            raise FileNotFoundError("No markdown files found in Mistral output")
        
        # Combine all markdown content
        combined_text = ""
        
        for md_file in markdown_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    page_content = f.read()
                    combined_text += page_content + "\n\n"
            except Exception as e:
                print(f"Error reading {md_file}: {e}")
                continue
        
        if not combined_text.strip():
            raise Exception("No text content extracted from PDF")
        
        self.text_content = combined_text.strip()
    
    def _extract_figures_metadata(self):
        """Extract figures and create metadata in expected format"""
        images_dir = self.mistral_output_dir / self.pdf_name / "images"
        json_dir = self.mistral_output_dir / self.pdf_name / "json"
        
        if not images_dir.exists() or not json_dir.exists():
            # No figures found - this is okay
            self.figures_metadata = []
            return
        
        # Process all extracted figures
        figures_metadata = []
        figure_counter = 1
        
        # Get all JSON files (one per page)
        json_files = sorted(json_dir.glob("*.json"))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    page_data = json.load(f)
                
                # Extract page info from filename
                page_match = re.search(r'page_(\d+)', json_file.name)
                page_num = int(page_match.group(1)) if page_match else 1
                
                # Process each page's data
                if 'pages' in page_data:
                    for page in page_data['pages']:
                        # Get markdown text for context
                        markdown_text = page.get('markdown', '')
                        
                        # Process images from this page
                        images = page.get('images', [])
                        
                        for img_data in images:
                            img_id = img_data.get('id', f"img_{figure_counter}")
                            
                            # Find the corresponding image file
                            image_filename = f"{self.pdf_name}_page_{page_num:02d}_{img_id}"
                            source_image_path = images_dir / image_filename
                            
                            if source_image_path.exists():
                                # Extract title and caption from markdown context
                                title, caption = self._extract_figure_info_from_markdown(
                                    markdown_text, img_id, figure_counter
                                )
                                
                                # Add to metadata (we'll copy files later in get_figures)
                                figures_metadata.append({
                                    "title": title,
                                    "caption": caption,
                                    "source_path": str(source_image_path),
                                    "figure_number": figure_counter
                                })
                                
                                figure_counter += 1
                            
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                continue
        
        self.figures_metadata = figures_metadata
    
    def _extract_figure_info_from_markdown(self, markdown_text, img_id, figure_num):
        """Extract figure title and caption from markdown text"""
        # Default values
        title = f"Figure {figure_num}"
        caption = "Figure extracted from document"
        
        try:
            # Look for figure references in the markdown
            figure_patterns = [
                rf"Figure\s+{figure_num}[:\.]?\s*([^\n]*)",
                rf"Fig\.\s+{figure_num}[:\.]?\s*([^\n]*)",
                rf"Figure\s+\d+[:\.]?\s*([^\n]*)",  # Any figure reference
                rf"Fig\.\s+\d+[:\.]?\s*([^\n]*)"   # Any fig reference
            ]
            
            for pattern in figure_patterns:
                matches = re.findall(pattern, markdown_text, re.IGNORECASE)
                if matches:
                    potential_caption = matches[0].strip()
                    if potential_caption:
                        if len(potential_caption) < 50:
                            title = f"Figure {figure_num}: {potential_caption}"
                        else:
                            sentences = potential_caption.split('.')
                            if len(sentences) > 1:
                                title = f"Figure {figure_num}: {sentences[0]}"
                                caption = potential_caption
                            else:
                                title = f"Figure {figure_num}"
                                caption = potential_caption
                        break
        except Exception as e:
            print(f"Error extracting figure info: {e}")
        
        return title, caption
    
    def get_text(self):
        """Get extracted text content"""
        if not self._processed:
            self.process_pdf()
        return self.text_content
    
    def get_figures(self, output_dir):
        """
        Get figures metadata and copy images to output directory
        Returns path to figures_metadata.json file
        """
        if not self._processed:
            self.process_pdf()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        if not self.figures_metadata:
            # No figures found - create empty metadata file
            figures_metadata_path = Path(output_dir) / "figures_metadata.json"
            with open(figures_metadata_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
            return str(figures_metadata_path)
        
        # Copy images and create final metadata
        final_metadata = []
        
        for fig_data in self.figures_metadata:
            source_path = Path(fig_data["source_path"])
            figure_num = fig_data["figure_number"]
            
            if source_path.exists():
                # Copy image to final output directory with standardized naming
                final_image_name = f"figure-{figure_num}.png"
                final_image_path = Path(output_dir) / final_image_name
                
                # Copy the image file
                import shutil
                shutil.copy2(source_path, final_image_path)
                
                # Add final metadata
                final_metadata.append({
                    "title": fig_data["title"],
                    "caption": fig_data["caption"],
                    "markdown_path": str(final_image_path)
                })
        
        # Write the figures_metadata.json file
        figures_metadata_path = Path(output_dir) / "figures_metadata.json"
        with open(figures_metadata_path, "w", encoding="utf-8") as f:
            json.dump(final_metadata, f, indent=2)
        
        print(f"Generated figures_metadata.json with {len(final_metadata)} figures")
        return str(figures_metadata_path)
    
    def cleanup(self):
        """Clean up temporary files"""
        if CLEANUP_TEMP_FILES and self.mistral_output_dir and self.mistral_output_dir.exists():
            import shutil
            shutil.rmtree(self.mistral_output_dir)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

# Convenience functions for backward compatibility
def extract_text_mistral(pdf_path):
    """Extract text using unified Mistral extractor"""
    with MistralExtractor(pdf_path) as extractor:
        return extractor.get_text()

def extract_figures_mistral(pdf_path, output_dir):
    """Extract figures using unified Mistral extractor"""
    with MistralExtractor(pdf_path) as extractor:
        return extractor.get_figures(output_dir)