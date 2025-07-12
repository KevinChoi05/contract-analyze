"""
Debug utilities for contract analysis system
Comprehensive logging and debugging methods
"""
import json
import logging
import traceback
from datetime import datetime
from typing import Any, Optional, Dict
import os
import re

# Configure debug logger
debug_logger = logging.getLogger('contract_debug')
debug_logger.setLevel(logging.DEBUG)

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# File handler
debug_handler = logging.FileHandler('logs/debug.log')
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
debug_logger.addHandler(debug_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('🔍 %(levelname)s: %(message)s'))
debug_logger.addHandler(console_handler)

def debug_deepseek_response(response_text: str, doc_id: Optional[int]) -> None:
    """Debug DeepSeek API response in detail."""
    doc_str = f" for Doc {doc_id}" if doc_id else ""
    debug_logger.info(f"🤖 DEEPSEEK RESPONSE DEBUG{doc_str}")
    debug_logger.info(f"📏 Response length: {len(response_text)} characters")
    debug_logger.info(f"🔤 First 200 chars: {response_text[:200]}...")
    debug_logger.info(f"🔤 Last 200 chars: ...{response_text[-200:]}")
    
    has_json_block = '```json' in response_text
    has_summary = 'summary' in response_text.lower()
    has_clauses = 'clause' in response_text.lower()
    
    debug_logger.info("🔍 Pattern Analysis:")
    debug_logger.info(f"   - Has JSON block: {has_json_block}")
    debug_logger.info(f"   - Has summary: {has_summary}")
    debug_logger.info(f"   - Has clauses: {has_clauses}")
    
    # Save full response
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    debug_file = f"logs/deepseek_response_{doc_id}_{timestamp}.txt" if doc_id else f"logs/deepseek_response_{timestamp}.txt"
    try:
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(f"DeepSeek Response{doc_str}\n")
            f.write(f"Timestamp: {datetime.now()}\n")
            f.write("=" * 50 + "\n")
            f.write(response_text)
        debug_logger.info(f"💾 Full response saved to: {debug_file}")
    except Exception as e:
        debug_logger.error(f"❌ Failed to save response file: {e}")

def debug_json_parsing(response_text: str, doc_id: Optional[int]) -> None:
    """Debug JSON parsing attempts."""
    doc_str = f" for Doc {doc_id}" if doc_id else ""
    debug_logger.info(f"🔧 JSON PARSING DEBUG{doc_str}")
    
    # Markdown extraction
    match = re.search(r'```json\s*\n(.*?)\n```', response_text, re.DOTALL)
    if match:
        json_content = match.group(1)
        debug_logger.info(f"✅ Found JSON markdown block ({len(json_content)} chars)")
        debug_logger.info(f"🔤 JSON preview: {json_content[:100]}...")
        try:
            parsed = json.loads(json_content)
            debug_logger.info("✅ Markdown JSON parsed")
            debug_logger.info(f"📊 Keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'Not a dict'}")
        except json.JSONDecodeError as e:
            debug_logger.error(f"❌ Markdown JSON parse failed: {e}")
    else:
        debug_logger.warning("⚠️ No JSON markdown block found")
    
    # Raw parsing
    try:
        parsed = json.loads(response_text)
        debug_logger.info("✅ Raw JSON parsed")
        debug_logger.info(f"📊 Keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'Not a dict'}")
    except json.JSONDecodeError as e:
        debug_logger.error(f"❌ Raw JSON parse failed: {e}")

def debug_string_parsing(response_text: str, doc_id: Optional[int]) -> None:
    """Debug string parsing fallback."""
    doc_str = f" for Doc {doc_id}" if doc_id else ""
    debug_logger.info(f"🔤 STRING PARSING DEBUG{doc_str}")
    
    # Summary extraction
    pattern = r'(?:Summary|SUMMARY|Executive Summary|Overview):\s*(.+?)(?=\n\n|\n(?:Identified|Risk)|$)'
    match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
    if match:
        summary = match.group(1).strip()
        debug_logger.info(f"✅ Summary found: {summary[:100]}...")
    else:
        debug_logger.warning("⚠️ No summary pattern matched, using first paragraph")
    
    # Clause parsing
    sections = re.split(r'\n\s*(?:\d+\.|•|\-|\*)\s*', response_text)
    debug_logger.info(f"📋 Found {len(sections)} potential sections")
    valid_clauses = 0
    for i, section in enumerate(sections[1:], 1):
        section = section.strip()
        if len(section) >= 20:
            valid_clauses += 1
            debug_logger.info(f"✅ Clause {i}: {section[:50]}...")
        else:
            debug_logger.info(f"⚠️ Clause {i}: Too short ({len(section)} chars)")
    debug_logger.info(f"📊 Valid clauses: {valid_clauses}")

def debug_analysis_result(analysis_result: Any, doc_id: Optional[int]) -> None:
    """Debug the final analysis result."""
    doc_str = f" for Doc {doc_id}" if doc_id else ""
    debug_logger.info(f"📊 ANALYSIS RESULT DEBUG{doc_str}")
    debug_logger.info(f"🔍 Type: {type(analysis_result)}")
    
    if isinstance(analysis_result, dict):
        debug_logger.info(f"📋 Keys: {list(analysis_result.keys())}")
        summary_len = len(analysis_result.get('summary', '')) 
        debug_logger.info(f"📝 Summary length: {summary_len} chars")
        clauses = analysis_result.get('clauses', [])
        debug_logger.info(f"📋 Clauses count: {len(clauses)}")
        for i, clause in enumerate(clauses[:3], 1):
            if isinstance(clause, dict):
                debug_logger.info(f"   Clause {i}: {clause.get('type', 'No type')} (Risk: {clause.get('risk_score', 'N/A')})")
            else:
                debug_logger.info(f"   Clause {i}: {type(clause)} - {str(clause)[:50]}...")
        if 'error' in analysis_result:
            debug_logger.error(f"❌ Error: {analysis_result['error']}")
    else:
        debug_logger.warning(f"⚠️ Not a dict: {str(analysis_result)[:100]}...")

def debug_db_storage(analysis_result: Dict, doc_id: Optional[int]) -> None:
    """Debug database storage of analysis."""
    doc_str = f" for Doc {doc_id}" if doc_id else ""
    debug_logger.info(f"💾 DB STORAGE DEBUG{doc_str}")
    try:
        json_str = json.dumps(analysis_result)
        debug_logger.info(f"✅ JSON serialized ({len(json_str)} chars)")
        parsed = json.loads(json_str)
        debug_logger.info("✅ Deserialized")
        debug_logger.info(f"📊 Keys: {list(parsed.keys())}")
    except Exception as e:
        debug_logger.error(f"❌ JSON failed: {e}")
        debug_logger.error(f"📊 Result: {analysis_result}")

def debug_template_data(document: Dict, doc_id: Optional[int]) -> None:
    """Debug template data structure."""
    doc_str = f" for Doc {doc_id}" if doc_id else ""
    debug_logger.info(f"🎨 TEMPLATE DATA DEBUG{doc_str}")
    debug_logger.info(f"📊 Keys: {list(document.keys())}")
    debug_logger.info(f"📊 Status: {document.get('status', 'Unknown')}")
    analysis = document.get('analysis')
    if analysis:
        debug_logger.info(f"🔍 Analysis type: {type(analysis)}")
        if isinstance(analysis, dict):
            debug_logger.info(f"📋 Keys: {list(analysis.keys())}")
            debug_logger.info("✅ Is mapping: True")
        else:
            debug_logger.info("⚠️ Is mapping: False")
            debug_logger.info(f"📝 Content: {str(analysis)[:100]}...")
    else:
        debug_logger.info("❌ No analysis data")

def debug_full_pipeline(doc_id: Optional[int], step: str, data: Any = None) -> None:
    """Debug the full pipeline at each step."""
    doc_str = f" - Doc {doc_id}" if doc_id else ""
    debug_logger.info(f"🔄 PIPELINE DEBUG{doc_str} - Step: {step}")
    if data is not None:
        debug_logger.info(f"📊 Data type: {type(data)}")
        debug_logger.info(f"📊 Preview: {str(data)[:200]}...")
    debug_logger.info(f"⏰ Timestamp: {datetime.now()}")

def enable_debug_mode():
    """Enable comprehensive debug mode."""
    debug_logger.info("🚀 DEBUG MODE ENABLED")
    debug_logger.info("📝 All analysis steps will be logged")
    debug_logger.info("💾 Responses saved to logs/")

def debug_error(error: Exception, context: str, doc_id: Optional[int] = None) -> None:
    """Debug error with full context."""
    doc_str = f" for Doc {doc_id}" if doc_id else ""
    debug_logger.error(f"❌ ERROR in {context}{doc_str}")
    debug_logger.error(f"🔍 Type: {type(error).__name__}")
    debug_logger.error(f"📝 Message: {str(error)}")
    debug_logger.error("📊 Traceback:")
    debug_logger.error(traceback.format_exc())