"""
Google Cloud Vision API OCR Service
Handles PDF to image conversion and text extraction using Vision API
"""
import os
import logging
from typing import Optional
from google.cloud import vision
import fitz  # PyMuPDF for PDF handling
from PIL import Image
import io
from google.oauth2 import service_account
import json

logger = logging.getLogger(__name__)

class VisionOCR:
    def __init__(self):
        self.client = self._initialize_client()

    def _initialize_client(self):
        credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if credentials_json:
            try:
                creds_dict = json.loads(credentials_json)
                credentials = service_account.Credentials.from_service_account_info(creds_dict)
                return vision.ImageAnnotatorClient(credentials=credentials)
            except Exception as e:
                logger.warning(f"Failed to initialize with JSON: {e}")
        try:
            return vision.ImageAnnotatorClient()
        except Exception as e:
            logger.warning(f"Failed to initialize with default credentials: {e}")
            return None

    def extract_text_from_pdf(self, file_path: str) -> Optional[str]:
        if not self.client:
            return None
        try:
            pdf = fitz.open(file_path)
            all_text = []
            for page_num in range(len(pdf)):
                page = pdf[page_num]
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                image = vision.Image(content=img_byte_arr.getvalue())
                response = self.client.document_text_detection(image=image)
                if response.full_text_annotation:
                    all_text.append(response.full_text_annotation.text.strip())
            pdf.close()
            full_text = '\n\n'.join(all_text)
            return full_text if full_text.strip() else None
        except Exception as e:
            logger.error(f"Vision PDF extraction failed: {e}")
            return None

# Global instance and functions as before 