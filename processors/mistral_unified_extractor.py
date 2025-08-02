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
            
            # Validate API key
            if not MISTRAL_API_KEY:
                raise Exception(
                    "MISTRAL_API_KEY environment variable is not set. "
                    "Please set it with: export MISTRAL_API_KEY='your-api-key'"
                )
            
            # Validate input file
            if not self.pdf_path.exists() or not self.pdf_path.is_file():
                raise Exception(f"PDF file does not exist or is not accessible: {self.pdf_path}")
            
            if self.pdf_path.suffix.lower() != '.pdf':
                raise Exception(f"File is not a PDF: {self.pdf_path}")
            
            print(f"Processing PDF with Mistral OCR: {self.pdf_path.name}")
            
            # Set up environment for the subprocess
            env = os.environ.copy()
            env["MISTRAL_API_KEY"] = MISTRAL_API_KEY
            
            cmd = [
                sys.executable,
                "extract_mistral_pdf.py",
                str(self.pdf_path),
                "--out", str(self.mistral_output_dir)
            ]
            
            print(f"Running command: {' '.join(cmd)}")
            print(f"Output directory: {self.mistral_output_dir}")
            
            # Execute the command and capture output
            result = subprocess.run(
                cmd, 
                check=False,  # Don't raise immediately, we'll handle it
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                error_details = []
                error_details.append(f"Command failed with exit code {result.returncode}")
                error_details.append(f"Command: {' '.join(cmd)}")
                
                if result.stdout:
                    error_details.append(f"STDOUT: {result.stdout.strip()}")
                
                if result.stderr:
                    error_details.append(f"STDERR: {result.stderr.strip()}")
                
                # Check for common issues
                if "MISTRAL_API_KEY environment variable is not set" in result.stderr:
                    error_details.append("SOLUTION: Set your Mistral API key: export MISTRAL_API_KEY='your-key'")
                elif "401" in result.stderr or "Unauthorized" in result.stderr:
                    error_details.append("SOLUTION: Check your Mistral API key is valid and has sufficient credits")
                elif "429" in result.stderr or "rate limit" in result.stderr.lower():
                    error_details.append("SOLUTION: Rate limit exceeded. Wait a moment and try again")
                elif "connection" in result.stderr.lower() or "network" in result.stderr.lower():
                    error_details.append("SOLUTION: Check your internet connection")
                
                raise Exception("Mistral OCR extraction failed:\n" + "\n".join(error_details))
            
            print(f"Mistral OCR completed successfully")
            
            # Cache the results
            self._extract_text_content()
            self._extract_figures_metadata()
            
            self._processed = True
            
        except subprocess.CalledProcessError as e:
            # This shouldn't happen anymore since we use check=False
            raise Exception(f"Subprocess error: {str(e)}")
        except Exception as e:
            # Re-raise with more context if it's our custom exception
            if "Mistral OCR extraction failed" in str(e):
                raise e
            else:
                raise Exception(f"Error processing PDF with Mistral OCR: {str(e)}")
    
    def _extract_text_content(self):
        """Extract and combine markdown text from all pages"""
        print(f"Extracting text content from Mistral output...")
        
        expected_pdf_dir = self.mistral_output_dir / self.pdf_name
        markdown_dir = expected_pdf_dir / "markdown"
        
        if not expected_pdf_dir.exists():
            raise Exception(
                f"Mistral output directory missing: {expected_pdf_dir}\n"
                f"Expected structure: {self.mistral_output_dir}/{self.pdf_name}/\n"
                f"Available directories: {list(self.mistral_output_dir.glob('*')) if self.mistral_output_dir.exists() else 'None'}"
            )
        
        if not markdown_dir.exists():
            available_dirs = list(expected_pdf_dir.glob("*"))
            raise Exception(
                f"Markdown directory not found: {markdown_dir}\n"
                f"Available subdirectories in {expected_pdf_dir}: {available_dirs}\n"
                f"Expected Mistral output structure: markdown/, images/, json/"
            )
        
        # Get all markdown files sorted by page number
        markdown_files = sorted(markdown_dir.glob("*.md"))
        
        if not markdown_files:
            raise Exception(
                f"No markdown files found in: {markdown_dir}\n"
                f"Directory contents: {list(markdown_dir.glob('*'))}\n"
                f"This suggests Mistral OCR didn't process any pages successfully"
            )
        
        print(f"Found {len(markdown_files)} markdown files to process")
        
        # Combine all markdown content
        combined_text = ""
        processed_files = 0
        
        for md_file in markdown_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    page_content = f.read()
                    if page_content.strip():  # Only add non-empty content
                        combined_text += page_content + "\n\n"
                        processed_files += 1
            except Exception as e:
                print(f"Warning: Error reading {md_file.name}: {e}")
                continue
        
        if not combined_text.strip():
            raise Exception(
                f"No text content extracted from PDF\n"
                f"Processed {processed_files} of {len(markdown_files)} markdown files\n"
                f"This could indicate the PDF is image-only or Mistral OCR failed to extract text"
            )
        
        self.text_content = combined_text.strip()
        print(f"Successfully extracted {len(self.text_content)} characters of text")
    
    def _extract_figures_metadata(self):
        """Extract figures and create metadata in expected format"""
        print(f"Extracting figures metadata from Mistral output...")
        
        expected_pdf_dir = self.mistral_output_dir / self.pdf_name
        images_dir = expected_pdf_dir / "images"
        json_dir = expected_pdf_dir / "json"
        
        if not images_dir.exists() and not json_dir.exists():
            print("No images or json directories found - no figures detected")
            self.figures_metadata = []
            return
        
        if not json_dir.exists():
            print(f"Warning: JSON directory not found: {json_dir}")
            self.figures_metadata = []
            return
        
        # Get all JSON files (one per page)
        json_files = sorted(json_dir.glob("*.json"))
        
        if not json_files:
            print(f"No JSON files found in: {json_dir}")
            self.figures_metadata = []
            return
        
        print(f"Processing {len(json_files)} JSON files for figure extraction")
        
        # Process all extracted figures
        figures_metadata = []
        figure_counter = 1
        processed_pages = 0
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    page_data = json.load(f)
                
                # Extract page info from filename
                page_match = re.search(r'page_(\d+)', json_file.name)
                page_num = int(page_match.group(1)) if page_match else 1
                
                # Process each page's data
                if 'pages' in page_data and page_data['pages']:
                    for page in page_data['pages']:
                        # Get markdown text for context
                        markdown_text = page.get('markdown', '')
                        
                        # Process images from this page
                        images = page.get('images', [])
                        
                        if images:
                            print(f"Found {len(images)} images on page {page_num}")
                        
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
                            else:
                                print(f"Warning: Expected image file not found: {source_image_path}")
                
                processed_pages += 1
                        
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in {json_file.name}: {e}")
                continue
            except Exception as e:
                print(f"Error processing {json_file.name}: {e}")
                continue
        
        self.figures_metadata = figures_metadata
        print(f"Successfully extracted metadata for {len(figures_metadata)} figures from {processed_pages} pages")
    
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