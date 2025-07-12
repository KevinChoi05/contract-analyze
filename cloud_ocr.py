import os
import logging
from typing import Optional
from google.cloud import documentai
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

class UnifiedOCR:
    """Unified OCR service using Google Cloud Document AI. This is a hard requirement."""
    
    def __init__(self):
        """Initialize the Document AI client. Raises exceptions if misconfigured."""
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        self.location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us')  # us, eu, asia
        self.processor_id = os.getenv('DOCUMENT_AI_PROCESSOR_ID')
        
        if not all([self.project_id, self.processor_id]):
            raise EnvironmentError(
                "Google Cloud Document AI not configured. "
                "Ensure GOOGLE_CLOUD_PROJECT_ID and DOCUMENT_AI_PROCESSOR_ID env vars are set."
            )
        
        credentials = None
        credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if credentials_json:
            try:
                import json
                creds_dict = json.loads(credentials_json)
                credentials = service_account.Credentials.from_service_account_info(creds_dict)
                logger.info("✅ Using JSON credentials for Google Cloud Document AI")
            except Exception as e:
                logger.warning(f"Failed to load JSON credentials: {e}")
        
        try:
            self.client = documentai.DocumentProcessorServiceClient(credentials=credentials)
            self.processor_name = f"projects/{self.project_id}/locations/{self.location}/processors/{self.processor_id}"
            logger.info("✅ Google Cloud Document AI initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Document AI client: {e}")
            raise ConnectionError(
                "Could not initialize Google Cloud Document AI client. "
                "Check credentials (default or GOOGLE_APPLICATION_CREDENTIALS_JSON)."
            )
    
    def _process_document(self, file_path: str) -> Optional[documentai.Document]:
        """Process the document and return the Document object."""
        try:
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                return None
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.error(f"File is empty: {file_path}")
                return None
            
            if file_size > 20 * 1024 * 1024:  # 20MB limit
                logger.error(f"File too large: {file_size} bytes")
                return None
            
            logger.info(f"Processing document: {file_path} ({file_size} bytes)")
            
            with open(file_path, 'rb') as file:
                file_content = file.read()
            
            mime_type = self._get_mime_type(file_path)
            raw_document = documentai.RawDocument(content=file_content, mime_type=mime_type)
            request = documentai.ProcessRequest(name=self.processor_name, raw_document=raw_document)
            
            result = self.client.process_document(request=request)
            return result.document
        
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            return None
    
    def extract_text(self, file_path: str) -> Optional[str]:
        """
        Extract text from any document using Document AI
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text or None if extraction fails
        """
        document = self._process_document(file_path)
        if not document:
            return None
        
        text = self._get_layout_text(document)
        if text and len(text.strip()) > 10:
            logger.info(f"✅ Extracted {len(text)} characters (layout-aware)")
            return text.strip()
        
        logger.warning("Layout extraction minimal, using raw text")
        raw_text = document.text.strip()
        if raw_text and len(raw_text) > 10:
            logger.info(f"✅ Extracted {len(raw_text)} characters (raw)")
            return raw_text
        
        logger.warning("Minimal or no text extracted")
        return None
    
    def _get_layout_text(self, document: documentai.Document) -> str:
        """Reconstruct text from document layout."""
        text = document.text
        paragraphs = []
        for page in document.pages:
            for paragraph in page.paragraphs:
                para_text = ''.join(
                    text[segment.start_index:segment.end_index]
                    for segment in paragraph.layout.text_anchor.text_segments
                ).strip()
                if para_text:
                    paragraphs.append(para_text)
        return '\n\n'.join(paragraphs)
    
    def _get_mime_type(self, file_path: str) -> str:
        """Determine MIME type based on file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp'
        }
        return mime_types.get(ext, 'application/pdf')
    
    def get_document_info(self, file_path: str) -> dict:
        """
        Get detailed document information.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with document metadata
        """
        document = self._process_document(file_path)
        if not document:
            return {"error": "Document processing failed"}
        
        return {
            "pages": len(document.pages),
            "text_length": len(document.text),
            "confidence": getattr(document, 'confidence', 0.0),
            "language": getattr(document, 'language', 'unknown'),
            "mime_type": self._get_mime_type(file_path)
        }

# Global OCR instance
_ocr_instance: Optional[UnifiedOCR] = None

def get_ocr_service() -> Optional[UnifiedOCR]:
    """
    Get the Google Cloud Document AI OCR service.
    Returns None if the service cannot be initialized, allowing fallback OCR.
    """
    global _ocr_instance
    if _ocr_instance is None:
        try:
            _ocr_instance = UnifiedOCR()
            logger.info("🚀 Google Cloud Document AI configured as OCR service.")
        except (EnvironmentError, ConnectionError) as e:
            logger.warning(f"Google Cloud OCR unavailable: {e}. Falling back to PyMuPDF.")
            _ocr_instance = None  # Explicit for clarity
    return _ocr_instance

def extract_text_unified(file_path: str) -> Optional[str]:
    """Proxy function to call the Google Cloud OCR service."""
    service = get_ocr_service()
    if service is None:
        return None
    try:
        return service.extract_text(file_path)
    except Exception as e:
        logger.error(f"Text extraction error: {e}")
        return None