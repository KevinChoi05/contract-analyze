"""
Core document processing logic
Handles text extraction, AI analysis, and status management
"""
import os
import re
import json
import logging
import openai
import time
from typing import Optional, Dict, Any
from datetime import datetime
import fitz  # PyMuPDF for fallback OCR
from database import get_db_connection
from cloud_ocr import get_ocr_service, extract_text_unified

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

def extract_text_fallback(file_path: str) -> Optional[str]:
    """
    Fallback text extraction using PyMuPDF when Google Cloud OCR is not available
    """
    try:
        logger.info(f"Using fallback OCR (PyMuPDF) for: {file_path}")
        
        # Open the document
        doc = fitz.open(file_path)
        text_content = []
        
        # Extract text from each page
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text.strip():
                text_content.append(text.strip())
        
        doc.close()
        
        # Combine all text
        full_text = '\n\n'.join(text_content)
        
        if full_text and len(full_text.strip()) > 10:
            logger.info(f"✅ Fallback OCR successful: {len(full_text)} characters")
            return full_text.strip()
        else:
            logger.warning("Fallback OCR extracted minimal or no text")
            return None
            
    except Exception as e:
        logger.error(f"Fallback OCR failed: {e}")
        return None

def extract_text_unified(file_path: str) -> Optional[str]:
    """
    Unified text extraction with fallback support
    """
    # Try Google Cloud OCR first
    try:
        ocr_service = get_ocr_service()
        if ocr_service:
            text = ocr_service.extract_text(file_path)
            if text:
                return text
    except Exception as e:
        logger.warning(f"Google Cloud OCR failed, trying fallback: {e}")
    
    # Fallback to PyMuPDF
    return extract_text_fallback(file_path)

def analyze_contract(text_content):
    """Analyzes contract text using DeepSeek and returns structured JSON."""
    if not DEEPSEEK_API_KEY:
        return {"error": "DeepSeek API Key not configured."}
    
    system_message = """You are an expert contract risk analyst. Your job is to identify business risks and provide EXACT SOURCE LOCATIONS.
CRITICAL REQUIREMENTS:
1. For each risk you identify, you MUST provide the exact sentence number where it appears
2. Use the [number] format from the text to reference source locations
3. Copy the EXACT text phrase that contains the risk (for highlighting)
4. Calculate precise 0-100 risk scores using the methodology below
RISK SCORING (0-100 Scale):
• 0-30: SAFE - Minimal impact, routine terms
• 31-69: WARNING - Moderate concern, needs attention  
• 70-100: UNSAFE - Critical threat, immediate action required
SCORING CRITERIA (weighted average):
1. Financial Impact (30%): 0-100 based on potential costs
2. Business Disruption (25%): 0-100 based on operational impact
3. Legal/Compliance Risk (20%): 0-100 based on legal exposure
4. Likelihood (15%): 0-100 based on probability of occurrence
5. Mitigation Difficulty (10%): 0-100 based on how hard to resolve
JSON RESPONSE FORMAT:
```json
{
  "summary": "A brief, one-paragraph executive summary of the contract's purpose and key risks.",
  "clauses": [
    {
      "id": 1,
      "exact_text": "Late payment will incur 5% monthly penalty plus immediate acceleration",
      "type": "Payment Default Penalties", 
      "risk_score": 75,
      "risk_category": "Unsafe",
      "clause": "Business-friendly description of the risk",
      "consequences": "What could happen to the business",
      "mitigation": "How to reduce this risk"
    }
  ]
}
```"""
    prompt = f"ANALYZE this contract and identify the TOP 8-10 MOST CRITICAL business risks. Return a valid JSON object.\n\nCONTRACT TEXT:\n{text_content[:24000]}"
    
    try:
        client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
                ],
            max_tokens=4096,
            temperature=0.1
        )
        response_text = response.choices[0].message.content
        # Extract JSON from markdown code block
        match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
        if match:
            return json.loads(match.group(1))
        else:
            return json.loads(response_text) # Fallback to parsing the whole string
    except Exception as e:
        logger.error(f"Error in analyze_contract: {e}")
        return {"error": f"Failed to analyze contract: {e}"} 