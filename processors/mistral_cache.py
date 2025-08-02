"""
Shared cache for Mistral OCR results to avoid duplicate API calls
"""

import threading
from pathlib import Path

class MistralCache:
    """Thread-safe cache for Mistral extractor instances"""
    
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()
    
    def get_or_create(self, pdf_path):
        """Get existing extractor or create new one"""
        pdf_key = str(Path(pdf_path).resolve())
        
        with self._lock:
            if pdf_key not in self._cache:
                from .mistral_unified_extractor import MistralExtractor
                self._cache[pdf_key] = MistralExtractor(pdf_path)
            
            return self._cache[pdf_key]
    
    def clear(self):
        """Clear the cache and cleanup extractors"""
        with self._lock:
            for extractor in self._cache.values():
                try:
                    extractor.cleanup()
                except:
                    pass
            self._cache.clear()
    
    def remove(self, pdf_path):
        """Remove specific PDF from cache"""
        pdf_key = str(Path(pdf_path).resolve())
        
        with self._lock:
            if pdf_key in self._cache:
                try:
                    self._cache[pdf_key].cleanup()
                except:
                    pass
                del self._cache[pdf_key]

# Global cache instance
_global_cache = MistralCache()

def get_mistral_extractor(pdf_path):
    """Get cached Mistral extractor for PDF"""
    return _global_cache.get_or_create(pdf_path)

def clear_mistral_cache():
    """Clear global Mistral cache"""
    _global_cache.clear()

def remove_from_cache(pdf_path):
    """Remove specific PDF from cache"""
    _global_cache.remove(pdf_path)