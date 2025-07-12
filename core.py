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

def extract_text_robust(file_path: str) -> Optional[str]:
    """
    Robust text extraction with multiple fallbacks
    Alias for extract_text_unified for backward compatibility
    """
    return extract_text_unified(file_path)

def extract_summary(content: str) -> str:
    """Extract summary from DeepSeek response text."""
    # Look for summary section
    summary_patterns = [
        r'Summary:\s*(.+?)(?=\n\n|\nIdentified|$)',
        r'SUMMARY:\s*(.+?)(?=\n\n|\nIDENTIFIED|$)',
        r'Executive Summary:\s*(.+?)(?=\n\n|\nRisk|$)',
        r'Overview:\s*(.+?)(?=\n\n|\nRisk|$)'
    ]
    
    for pattern in summary_patterns:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Fallback: use first paragraph
    lines = content.split('\n')
    for line in lines:
        if line.strip() and len(line.strip()) > 50:
            return line.strip()
    
    return "Contract analysis completed."

def parse_clauses(content: str) -> list:
    """Parse clauses from DeepSeek response text."""
    clauses = []
    
    # Split by common clause separators
    clause_sections = re.split(r'\n\s*(?:\d+\.|•|\-|\*)\s*', content)
    
    for i, section in enumerate(clause_sections[1:], 1):  # Skip first empty section
        if len(section.strip()) < 20:
            continue
            
        # Extract clause components
        clause_data = {
            'id': i,
            'type': 'Contract Clause',
            'risk_score': 50,  # Default medium risk
            'clause': section.strip()[:200] + '...' if len(section.strip()) > 200 else section.strip(),
            'consequences': 'Potential business impact requires review.',
            'mitigation': 'Consult legal counsel for specific guidance.',
            'exact_text': section.strip()[:300] + '...' if len(section.strip()) > 300 else section.strip()
        }
        
        # Try to extract risk score
        risk_match = re.search(r'(?:risk|score):\s*(\d+)', section, re.IGNORECASE)
        if risk_match:
            clause_data['risk_score'] = int(risk_match.group(1))
        
        # Try to extract clause type
        type_match = re.search(r'(?:type|category):\s*([^\n]+)', section, re.IGNORECASE)
        if type_match:
            clause_data['type'] = type_match.group(1).strip()
        
        clauses.append(clause_data)
        
        # Limit to 10 clauses
        if len(clauses) >= 10:
            break
    
    return clauses

def analyze_contract(text_content, doc_id=None):
    """Analyzes contract text using DeepSeek and returns structured JSON."""
    # Import debug utilities
    try:
        from debug_utils import debug_full_pipeline, debug_deepseek_response, debug_json_parsing, debug_string_parsing, debug_analysis_result, debug_error
    except ImportError:
        # Fallback if debug_utils not available
        def debug_full_pipeline(*args, **kwargs): pass
        def debug_deepseek_response(*args, **kwargs): pass
        def debug_json_parsing(*args, **kwargs): pass
        def debug_string_parsing(*args, **kwargs): pass
        def debug_analysis_result(*args, **kwargs): pass
        def debug_error(*args, **kwargs): pass
    
    debug_full_pipeline(doc_id, "analyze_contract_start", f"Text length: {len(text_content)}")
    
    if not DEEPSEEK_API_KEY:
        error_result = {"error": "DeepSeek API Key not configured."}
        debug_analysis_result(error_result, doc_id)
        return error_result
    
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
        debug_full_pipeline(doc_id, "deepseek_api_call")
        
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
        logger.info(f"🤖 DeepSeek raw response: {response_text[:500]}...")
        
        # 🔍 DEBUG: Analyze DeepSeek response
        debug_deepseek_response(response_text, doc_id)
        
        # Try to extract JSON from markdown code block
        debug_full_pipeline(doc_id, "json_parsing_attempt")
        debug_json_parsing(response_text, doc_id)
        
        match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
        if match:
            try:
                parsed_json = json.loads(match.group(1))
                logger.info(f"✅ Successfully parsed JSON from markdown block")
                debug_analysis_result(parsed_json, doc_id)
                return parsed_json
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse JSON from markdown block, trying string parsing")
                debug_error(e, "markdown_json_parsing", doc_id)
        
        # Try to parse the whole response as JSON
        try:
            parsed_json = json.loads(response_text)
            logger.info(f"✅ Successfully parsed raw response as JSON")
            debug_analysis_result(parsed_json, doc_id)
            return parsed_json
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse as JSON, falling back to string parsing")
            debug_error(e, "raw_json_parsing", doc_id)
        
        # 🚨 FALLBACK: Parse string response into structured dict
        debug_full_pipeline(doc_id, "string_parsing_fallback")
        debug_string_parsing(response_text, doc_id)
        
        logger.info(f"🔄 Parsing string response into structured format")
        summary = extract_summary(response_text)
        clauses = parse_clauses(response_text)
        
        structured_result = {
            'summary': summary,
            'clauses': clauses
        }
        
        logger.info(f"✅ String parsing successful: {len(clauses)} clauses extracted")
        debug_analysis_result(structured_result, doc_id)
        return structured_result
        
    except Exception as e:
        logger.error(f"Error in analyze_contract: {e}")
        debug_error(e, "analyze_contract", doc_id)
        
        # Return structured error instead of string
        error_result = {
            "error": f"Failed to analyze contract: {e}",
            "summary": "Analysis failed due to technical issues.",
            "clauses": []
        }
        debug_analysis_result(error_result, doc_id)
        return error_result 