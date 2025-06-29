import os
import re
import json
import logging
import openai
from cloud_ocr import extract_text_unified

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

def extract_text_robust(filepath):
    """
    Unified text extraction using Google Cloud Document AI or fallback
    This replaces all the complex OCR logic with a single, reliable method
    """
    logger.info(f"Starting unified text extraction for: {filepath}")
    
    try:
        # Use unified OCR service
        text = extract_text_unified(filepath)
                
        if text and len(text.strip()) > 10:
            logger.info(f"✅ Unified OCR extraction successful: {len(text)} characters")
            return text
        else:
            logger.warning("Unified OCR extracted minimal or no text")
            return None
            
    except Exception as e:
        logger.error(f"Unified OCR extraction failed: {e}")
        return None

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