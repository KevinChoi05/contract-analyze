"""
Debug utilities for contract analysis system
Comprehensive logging and debugging methods
"""
import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
import os

# Configure debug logger
debug_logger = logging.getLogger('contract_debug')
debug_logger.setLevel(logging.DEBUG)

# Create debug log file handler
debug_handler = logging.FileHandler('logs/debug.log')
debug_handler.setLevel(logging.DEBUG)
debug_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
debug_handler.setFormatter(debug_formatter)
debug_logger.addHandler(debug_handler)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('🔍 %(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)
debug_logger.addHandler(console_handler)

def debug_deepseek_response(response_text: str, doc_id: int) -> None:
    """Debug DeepSeek API response in detail."""
    debug_logger.info(f"🤖 DEEPSEEK RESPONSE DEBUG for Doc {doc_id}")
    debug_logger.info(f"📏 Response length: {len(response_text)} characters")
    debug_logger.info(f"🔤 First 200 chars: {response_text[:200]}...")
    debug_logger.info(f"🔤 Last 200 chars: ...{response_text[-200:]}")
    
    # Check for common patterns
    has_json_block = '```json' in response_text
    has_summary = 'summary' in response_text.lower()
    has_clauses = 'clause' in response_text.lower()
    
    debug_logger.info(f"🔍 Pattern Analysis:")
    debug_logger.info(f"   - Has JSON block: {has_json_block}")
    debug_logger.info(f"   - Has summary: {has_summary}")
    debug_logger.info(f"   - Has clauses: {has_clauses}")
    
    # Save full response to file for inspection
    debug_file = f"logs/deepseek_response_{doc_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(f"DeepSeek Response for Document {doc_id}\n")
            f.write(f"Timestamp: {datetime.now()}\n")
            f.write("="*50 + "\n")
            f.write(response_text)
        debug_logger.info(f"💾 Full response saved to: {debug_file}")
    except Exception as e:
        debug_logger.error(f"❌ Failed to save response file: {e}")

def debug_json_parsing(response_text: str, doc_id: int) -> None:
    """Debug JSON parsing attempts."""
    debug_logger.info(f"🔧 JSON PARSING DEBUG for Doc {doc_id}")
    
    # Test markdown JSON extraction
    import re
    match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
    if match:
        json_content = match.group(1)
        debug_logger.info(f"✅ Found JSON markdown block ({len(json_content)} chars)")
        debug_logger.info(f"🔤 JSON content preview: {json_content[:100]}...")
        
        try:
            parsed = json.loads(json_content)
            debug_logger.info(f"✅ Markdown JSON parsed successfully")
            debug_logger.info(f"📊 Keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'Not a dict'}")
        except json.JSONDecodeError as e:
            debug_logger.error(f"❌ Markdown JSON parse failed: {e}")
    else:
        debug_logger.warning(f"⚠️ No JSON markdown block found")
    
    # Test raw JSON parsing
    try:
        parsed = json.loads(response_text)
        debug_logger.info(f"✅ Raw JSON parsed successfully")
        debug_logger.info(f"📊 Keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'Not a dict'}")
    except json.JSONDecodeError as e:
        debug_logger.error(f"❌ Raw JSON parse failed: {e}")

def debug_string_parsing(response_text: str, doc_id: int) -> None:
    """Debug string parsing fallback."""
    debug_logger.info(f"🔤 STRING PARSING DEBUG for Doc {doc_id}")
    
    # Test summary extraction
    summary_patterns = [
        r'Summary:\s*(.+?)(?=\n\n|\nIdentified|$)',
        r'SUMMARY:\s*(.+?)(?=\n\n|\nIDENTIFIED|$)',
        r'Executive Summary:\s*(.+?)(?=\n\n|\nRisk|$)',
        r'Overview:\s*(.+?)(?=\n\n|\nRisk|$)'
    ]
    
    summary_found = False
    for i, pattern in enumerate(summary_patterns):
        match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
        if match:
            summary = match.group(1).strip()
            debug_logger.info(f"✅ Summary found with pattern {i+1}: {summary[:100]}...")
            summary_found = True
            break
    
    if not summary_found:
        debug_logger.warning(f"⚠️ No summary pattern matched, using first paragraph")
    
    # Test clause parsing
    import re
    clause_sections = re.split(r'\n\s*(?:\d+\.|•|\-|\*)\s*', response_text)
    debug_logger.info(f"📋 Found {len(clause_sections)} potential clause sections")
    
    valid_clauses = 0
    for i, section in enumerate(clause_sections[1:], 1):
        if len(section.strip()) >= 20:
            valid_clauses += 1
            debug_logger.info(f"✅ Clause {i}: {section.strip()[:50]}...")
        else:
            debug_logger.info(f"⚠️ Clause {i}: Too short ({len(section.strip())} chars)")
    
    debug_logger.info(f"📊 Valid clauses: {valid_clauses}")

def debug_analysis_result(analysis_result: Any, doc_id: int) -> None:
    """Debug the final analysis result."""
    debug_logger.info(f"📊 ANALYSIS RESULT DEBUG for Doc {doc_id}")
    debug_logger.info(f"🔍 Type: {type(analysis_result)}")
    
    if isinstance(analysis_result, dict):
        debug_logger.info(f"📋 Keys: {list(analysis_result.keys())}")
        
        if 'summary' in analysis_result:
            summary_len = len(analysis_result['summary']) if analysis_result['summary'] else 0
            debug_logger.info(f"📝 Summary length: {summary_len} chars")
        
        if 'clauses' in analysis_result:
            clauses = analysis_result['clauses']
            debug_logger.info(f"📋 Clauses count: {len(clauses) if clauses else 0}")
            
            if clauses:
                for i, clause in enumerate(clauses[:3], 1):  # Show first 3 clauses
                    if isinstance(clause, dict):
                        debug_logger.info(f"   Clause {i}: {clause.get('type', 'No type')} (Risk: {clause.get('risk_score', 'N/A')})")
                    else:
                        debug_logger.info(f"   Clause {i}: {type(clause)} - {str(clause)[:50]}...")
        
        if 'error' in analysis_result:
            debug_logger.error(f"❌ Analysis contains error: {analysis_result['error']}")
    else:
        debug_logger.warning(f"⚠️ Analysis result is not a dict: {str(analysis_result)[:100]}...")

def debug_db_storage(analysis_result: Dict, doc_id: int) -> None:
    """Debug database storage of analysis."""
    debug_logger.info(f"💾 DB STORAGE DEBUG for Doc {doc_id}")
    
    try:
        json_str = json.dumps(analysis_result)
        debug_logger.info(f"✅ JSON serialization successful ({len(json_str)} chars)")
        
        # Test deserialization
        parsed_back = json.loads(json_str)
        debug_logger.info(f"✅ JSON deserialization successful")
        debug_logger.info(f"📊 Roundtrip keys: {list(parsed_back.keys())}")
        
    except Exception as e:
        debug_logger.error(f"❌ JSON serialization failed: {e}")
        debug_logger.error(f"📊 Analysis result: {analysis_result}")

def debug_template_data(document: Dict, doc_id: int) -> None:
    """Debug template data structure."""
    debug_logger.info(f"🎨 TEMPLATE DATA DEBUG for Doc {doc_id}")
    debug_logger.info(f"📊 Document keys: {list(document.keys())}")
    debug_logger.info(f"📊 Status: {document.get('status', 'Unknown')}")
    
    analysis = document.get('analysis')
    if analysis:
        debug_logger.info(f"🔍 Analysis type: {type(analysis)}")
        
        if isinstance(analysis, dict):
            debug_logger.info(f"📋 Analysis keys: {list(analysis.keys())}")
            debug_logger.info(f"✅ Analysis is mapping: True")
        else:
            debug_logger.info(f"⚠️ Analysis is mapping: False")
            debug_logger.info(f"📝 Analysis content: {str(analysis)[:100]}...")
    else:
        debug_logger.info(f"❌ No analysis data")

def debug_full_pipeline(doc_id: int, step: str, data: Any = None) -> None:
    """Debug the full pipeline at each step."""
    debug_logger.info(f"🔄 PIPELINE DEBUG - Doc {doc_id} - Step: {step}")
    
    if data is not None:
        debug_logger.info(f"📊 Data type: {type(data)}")
        debug_logger.info(f"📊 Data preview: {str(data)[:200]}...")
    
    # Log current timestamp for timing analysis
    debug_logger.info(f"⏰ Timestamp: {datetime.now()}")

def enable_debug_mode():
    """Enable comprehensive debug mode."""
    debug_logger.info("🚀 DEBUG MODE ENABLED")
    debug_logger.info("📝 All contract analysis steps will be logged")
    debug_logger.info("💾 Response files will be saved to logs/")
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)

def debug_error(error: Exception, context: str, doc_id: int = None) -> None:
    """Debug error with full context."""
    debug_logger.error(f"❌ ERROR in {context}" + (f" for Doc {doc_id}" if doc_id else ""))
    debug_logger.error(f"🔍 Error type: {type(error).__name__}")
    debug_logger.error(f"📝 Error message: {str(error)}")
    debug_logger.error(f"📊 Traceback:")
    debug_logger.error(traceback.format_exc()) 