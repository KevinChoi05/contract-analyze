"""
Core document processing logic
Handles text extraction, AI analysis, and status management
"""
import os
import re
import json
import logging
import openai
from typing import Optional, Dict, Any
import fitz  # PyMuPDF for fallback OCR
from database import get_db_connection
from cloud_ocr import get_ocr_service, extract_text_unified as cloud_extract_text

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

def extract_text_fallback(file_path: str) -> Optional[str]:
    """
    Fallback text extraction using PyMuPDF when Google Cloud OCR is not available
    """
    try:
        logger.info(f"Using fallback OCR (PyMuPDF) for: {file_path}")
        with fitz.open(file_path) as doc:
            text_content = []
            for page in doc:
                text = page.get_text().strip()
                if text:
                    text_content.append(text)
        full_text = '\n\n'.join(text_content).strip()
        if len(full_text) > 10:
            logger.info(f"✅ Fallback OCR successful: {len(full_text)} characters")
            return full_text
        logger.warning("Fallback OCR extracted minimal or no text")
        return None
    except Exception as e:
        logger.error(f"Fallback OCR failed: {e}")
        return None

def extract_text_unified(file_path: str) -> Optional[str]:
    """
    Unified text extraction with fallback support
    """
    ocr_service = get_ocr_service()
    if ocr_service:
        text = cloud_extract_text(file_path)
        if text:
            return text
    return extract_text_fallback(file_path)

def extract_summary(content: str) -> str:
    """Extract summary from DeepSeek response text."""
    patterns = [
        r'(?:Summary|SUMMARY|Executive Summary|Overview):\s*(.+?)(?=\n\n|\n(?:Identified|Risk)|$)'
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    lines = [line.strip() for line in content.split('\n') if len(line.strip()) > 50]
    return lines[0] if lines else "Contract analysis completed."

def parse_clauses(content: str) -> list:
    """Parse clauses from DeepSeek response text."""
    clauses = []
    sections = re.split(r'\n\s*(?:\d+\.|•|\-|\*)\s*', content)
    for i, section in enumerate(sections[1:], 1):  # Skip first
        section = section.strip()
        if len(section) < 20:
            continue
        clause_data = {
            'id': i,
            'type': 'Contract Clause',
            'risk_score': 50,
            'clause': section[:200] + '...' if len(section) > 200 else section,
            'consequences': 'Potential business impact requires review.',
            'mitigation': 'Consult legal counsel for specific guidance.',
            'exact_text': section[:300] + '...' if len(section) > 300 else section
        }
        risk_match = re.search(r'(?:risk|score):\s*(\d+)', section, re.IGNORECASE)
        if risk_match:
            clause_data['risk_score'] = int(risk_match.group(1))
        type_match = re.search(r'(?:type|category):\s*([^\n]+)', section, re.IGNORECASE)
        if type_match:
            clause_data['type'] = type_match.group(1).strip()
        clauses.append(clause_data)
        if len(clauses) >= 10:
            break
    return clauses

def analyze_contract(text_content: str, doc_id: Optional[str] = None) -> Dict[str, Any]:
    """Analyzes contract text using DeepSeek and returns structured JSON."""
    try:
        from debug_utils import (
            debug_full_pipeline, debug_deepseek_response, debug_json_parsing,
            debug_string_parsing, debug_analysis_result, debug_error
        )
    except ImportError:
        debug_full_pipeline = debug_deepseek_response = debug_json_parsing = \
        debug_string_parsing = debug_analysis_result = debug_error = lambda *args, **kwargs: None
    
    debug_full_pipeline(doc_id, "analyze_contract_start", f"Text length: {len(text_content)}")
    
    if not DEEPSEEK_API_KEY:
        error_result = {"error": "DeepSeek API Key not configured.", "summary": "", "clauses": []}
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
        response_text = response.choices[0].message.content.strip()
        logger.info(f"🤖 DeepSeek raw response: {response_text[:500]}...")
        debug_deepseek_response(response_text, doc_id)
        
        # Attempt JSON parsing
        debug_full_pipeline(doc_id, "json_parsing_attempt")
        debug_json_parsing(response_text, doc_id)
        
        # Extract from markdown if present
        match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
        json_str = match.group(1) if match else response_text
        
        try:
            parsed_json = json.loads(json_str)
            logger.info("✅ Parsed JSON successfully")
            debug_analysis_result(parsed_json, doc_id)
            return parsed_json
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing failed, using string fallback")
            debug_error(e, "json_parsing", doc_id)
        
        # String parsing fallback
        debug_full_pipeline(doc_id, "string_parsing_fallback")
        debug_string_parsing(response_text, doc_id)
        summary = extract_summary(response_text)
        clauses = parse_clauses(response_text)
        result = {'summary': summary, 'clauses': clauses}
        logger.info(f"✅ String parsing: {len(clauses)} clauses")
        debug_analysis_result(result, doc_id)
        return result
    
    except Exception as e:
        logger.error(f"Error in analyze_contract: {e}")
        debug_error(e, "analyze_contract", doc_id)
        error_result = {
            "error": f"Failed to analyze contract: {str(e)}",
            "summary": "Analysis failed due to technical issues.",
            "clauses": []
        }
        debug_analysis_result(error_result, doc_id)
        return error_result