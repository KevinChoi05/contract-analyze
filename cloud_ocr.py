"""
Unified OCR using Google Cloud Document AI
Handles any type of document with enterprise-grade accuracy
"""
import os
import logging
from typing import Optional
from google.cloud import documentai
from google.cloud import storage
import tempfile

logger = logging.getLogger(__name__)

class UnifiedOCR:
    """Unified OCR service using Google Cloud Document AI"""
    
    def __init__(self):
        """Initialize the Document AI client"""
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        self.location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us')  # us, eu, asia
        self.processor_id = os.getenv('DOCUMENT_AI_PROCESSOR_ID')
        
        # Check if all required config is present
        if not all([self.project_id, self.processor_id]):
            logger.info("🔧 Google Cloud Document AI not configured - using fallback OCR")
            self.client = None
            self.available = False
            return
        
        # Handle Railway environment variable for service account JSON
        credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if credentials_json:
            try:
                import json
                import tempfile
                from google.oauth2 import service_account
                
                # Parse JSON credentials
                creds_dict = json.loads(credentials_json)
                
                # Create credentials from dict
                credentials = service_account.Credentials.from_service_account_info(creds_dict)
                
                # Initialize client with credentials
                self.client = documentai.DocumentProcessorServiceClient(credentials=credentials)
                self.processor_name = f"projects/{self.project_id}/locations/{self.location}/processors/{self.processor_id}"
                logger.info("✅ Google Cloud Document AI initialized with JSON credentials")
                self.available = True
                return
                
            except Exception as e:
                logger.warning(f"Failed to initialize with JSON credentials: {e}")
        
        # Try default credentials (for local development)
        try:
            self.client = documentai.DocumentProcessorServiceClient()
            self.processor_name = f"projects/{self.project_id}/locations/{self.location}/processors/{self.processor_id}"
            logger.info("✅ Google Cloud Document AI initialized with default credentials")
            self.available = True
        except Exception as e:
            logger.warning(f"❌ Google Cloud Document AI not available: {e}")
            logger.info("💡 Tip: Set GOOGLE_APPLICATION_CREDENTIALS_JSON for Railway deployment")
            self.client = None
            self.available = False
    
    def extract_text(self, file_path: str) -> Optional[str]:
        """
        Extract text from any document using Document AI
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text or None if extraction fails
        """
        if not self.available:
            logger.error("Document AI not available - check credentials and configuration")
            return None
        
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
            
            # Extract text
            text = document.text
            
            if text and len(text.strip()) > 10:
                logger.info(f"✅ Document AI extraction successful: {len(text)} characters")
                return text.strip()
            else:
                logger.warning("Document AI extracted minimal or no text")
                return None
                
        except Exception as e:
            logger.error(f"Document AI extraction failed: {e}")
            return None
    
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
        if not self.available:
            return {"error": "Document AI not available"}
        
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


# Fallback OCR for when Google Cloud is not available
class FallbackOCR:
    """Simple fallback OCR using PyMuPDF only"""
    
    def __init__(self):
        self.available = True
        logger.info("📄 Fallback OCR (PyMuPDF only) initialized")
    
    def extract_text(self, file_path: str) -> Optional[str]:
        """Extract text using PyMuPDF only"""
        try:
            import fitz  # PyMuPDF
            
            if not os.path.exists(file_path):
                return None
            
            with fitz.open(file_path) as doc:
                if doc.page_count == 0:
                    return None
                
                text_parts = []
                for page in doc:
                    page_text = page.get_text()
                    if page_text.strip():
                        text_parts.append(page_text)
                
                text = " ".join(text_parts)
                
                if len(text.strip()) > 10:
                    logger.info(f"📄 Fallback OCR extracted {len(text)} characters")
                    return text.strip()
                
            return None
            
        except Exception as e:
            logger.error(f"Fallback OCR failed: {e}")
            return None


# Global OCR instance
_ocr_instance = None

def get_ocr_service():
    """Get the best available OCR service"""
    global _ocr_instance
    
    if _ocr_instance is None:
        # Try Google Cloud Document AI first
        unified_ocr = UnifiedOCR()
        if unified_ocr.available:
            _ocr_instance = unified_ocr
            logger.info("🚀 Using Google Cloud Document AI for OCR")
        else:
            _ocr_instance = FallbackOCR()
            logger.info("📄 Using fallback OCR (PyMuPDF only)")
    
    return _ocr_instance


def extract_text_unified(file_path: str) -> Optional[str]:
    """
    Unified text extraction function
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Extracted text or None if extraction fails
    """
    ocr_service = get_ocr_service()
    return ocr_service.extract_text(file_path) 