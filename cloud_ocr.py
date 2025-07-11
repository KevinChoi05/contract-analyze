"""
Unified OCR using Google Cloud Document AI
Handles any type of document with enterprise-grade accuracy
"""
import os
import logging
from typing import Optional
from google.cloud import documentai

logger = logging.getLogger(__name__)

class UnifiedOCR:
    """Unified OCR service using Google Cloud Document AI. This is a hard requirement."""
    
    def __init__(self):
        """Initialize the Document AI client. Raises exceptions if misconfigured."""
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        self.location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us')  # us, eu, asia
        self.processor_id = os.getenv('DOCUMENT_AI_PROCESSOR_ID')
        
        # Check if all required config is present
        if not all([self.project_id, self.processor_id]):
            raise EnvironmentError(
                "Google Cloud Document AI not configured. "
                "Ensure GOOGLE_CLOUD_PROJECT_ID and DOCUMENT_AI_PROCESSOR_ID env vars are set."
            )
        
        # Handle Railway environment variable for service account JSON
        credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        initialized = False
        if credentials_json:
            try:
                import json
                from google.oauth2 import service_account
                
                creds_dict = json.loads(credentials_json)
                credentials = service_account.Credentials.from_service_account_info(creds_dict)
                
                self.client = documentai.DocumentProcessorServiceClient(credentials=credentials)
                self.processor_name = f"projects/{self.project_id}/locations/{self.location}/processors/{self.processor_id}"
                logger.info("✅ Google Cloud Document AI initialized with JSON credentials")
                initialized = True
            except Exception as e:
                logger.warning(f"Failed to initialize with JSON credentials: {e}")

        # Try default credentials if not initialized via JSON
        if not initialized:
            try:
                self.client = documentai.DocumentProcessorServiceClient()
                self.processor_name = f"projects/{self.project_id}/locations/{self.location}/processors/{self.processor_id}"
                logger.info("✅ Google Cloud Document AI initialized with default credentials")
                initialized = True
            except Exception as e:
                logger.warning(f"Failed to initialize with default credentials: {e}")
        
        if not initialized:
            raise ConnectionError(
                "Could not initialize Google Cloud Document AI client. "
                "Check credentials (default or GOOGLE_APPLICATION_CREDENTIALS_JSON)."
            )
    
    def extract_text(self, file_path: str) -> Optional[str]:
        """
        Extract text from any document using Document AI
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text or None if extraction fails
        """
        try:
            # Validate file
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                return None
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.error(f"File is empty: {file_path}")
                return None
            
            if file_size > 20 * 1024 * 1024:  # 20MB limit for Document AI
                logger.error(f"File too large for Document AI: {file_size} bytes")
                return None
            
            logger.info(f"Processing document with Document AI: {file_path} ({file_size} bytes)")
            
            # Read file content
            with open(file_path, 'rb') as file:
                file_content = file.read()
            
            # Determine MIME type
            mime_type = self._get_mime_type(file_path)
            
            # Create Document AI request
            raw_document = documentai.RawDocument(
                content=file_content,
                mime_type=mime_type
            )
            
            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document
            )
            
            # Process document
            result = self.client.process_document(request=request)
            document = result.document
            
            # Extract text using the new layout-aware method
            text = self._get_layout_text(document)
            
            if text and len(text.strip()) > 10:
                logger.info(f"✅ Document AI extraction successful: {len(text)} characters")
                return text.strip()
            else:
                logger.warning("Layout-aware text extraction yielded minimal text, trying raw text fallback.")
                # Fallback to raw text if layout parsing is empty
                raw_text = document.text.strip()
                if raw_text and len(raw_text) > 10:
                    logger.info(f"✅ Using raw text fallback: {len(raw_text)} characters")
                    return raw_text
                
                logger.warning("Document AI extracted minimal or no text in both layout and raw modes.")
                return None
                
        except Exception as e:
            logger.error(f"Document AI extraction failed: {e}")
            return None
    
    def _get_layout_text(self, document: documentai.Document) -> str:
        """
        Reconstructs text from the document layout, preserving paragraphs.
        This provides a cleaner, more readable output than the raw text dump.
        """
        text = document.text
        output_paragraphs = []

        for page in document.pages:
            for paragraph in page.paragraphs:
                # Get the text for the paragraph by slicing the full text
                paragraph_text = ''.join(
                    text[segment.start_index:segment.end_index]
                    for segment in paragraph.layout.text_anchor.text_segments
                )
                output_paragraphs.append(paragraph_text.strip())
        
        # Join all paragraphs with double newlines for clear separation,
        # creating a format that's easier for other AI models to read.
        return '\n\n'.join(output_paragraphs)
    
    def _get_mime_type(self, file_path: str) -> str:
        """Determine MIME type based on file extension"""
        extension = os.path.splitext(file_path)[1].lower()
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
        return mime_types.get(extension, 'application/pdf')
    
    def get_document_info(self, file_path: str) -> dict:
        """
        Get detailed document information including pages, confidence, etc.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with document metadata
        """
        try:
            with open(file_path, 'rb') as file:
                file_content = file.read()
            
            mime_type = self._get_mime_type(file_path)
            
            raw_document = documentai.RawDocument(
                content=file_content,
                mime_type=mime_type
            )
            
            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document
            )
            
            result = self.client.process_document(request=request)
            document = result.document
            
            return {
                "pages": len(document.pages),
                "text_length": len(document.text),
                "confidence": getattr(document, 'confidence', 0.0),
                "language": getattr(document, 'language', 'unknown'),
                "mime_type": mime_type
            }
            
        except Exception as e:
            logger.error(f"Failed to get document info: {e}")
            return {"error": str(e)}


# Global OCR instance
_ocr_instance = None

def get_ocr_service():
    """
    Get the Google Cloud Document AI OCR service.
    Returns None if the service cannot be initialized, allowing fallback OCR.
    """
    global _ocr_instance
    
    if _ocr_instance is None:
        try:
            _ocr_instance = UnifiedOCR()
            logger.info("🚀 Google Cloud Document AI is the configured OCR service.")
        except (EnvironmentError, ConnectionError) as e:
            logger.warning(f"Google Cloud OCR not available: {e}")
            logger.info("📄 Using fallback OCR (PyMuPDF) for document processing.")
            _ocr_instance = None
    
    return _ocr_instance

def extract_text_unified(file_path: str) -> Optional[str]:
    """Proxy function to call the Google Cloud OCR service"""
    try:
        # The service is initialized at startup, so we can expect it to be here.
        service = get_ocr_service()
        return service.extract_text(file_path)
    except Exception as e:
        # This will catch errors during the *call* to extract_text,
        # not initialization, which is what we want.
        logger.error(f"An unexpected error occurred during text extraction: {e}")
        return None 