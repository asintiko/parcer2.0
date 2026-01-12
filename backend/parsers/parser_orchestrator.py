"""
Parser orchestrator - coordinates regex and GPT parsers with operator mapping
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from parsers.regex_parser import RegexParser
from parsers.gpt_parser import GPTParser
from parsers.operator_mapper import OperatorMapper


class ParserOrchestrator:
    """Main parsing coordinator that cascades through parsing strategies"""
    
    def __init__(self, db_session: Session, openai_api_key: Optional[str] = None):
        self.regex_parser = RegexParser()
        self.gpt_parser = GPTParser(api_key=openai_api_key)
        self.operator_mapper = OperatorMapper(db_session)
        
        # Confidence threshold for accepting regex results
        self.confidence_threshold = 0.8
    
    def process(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """
        Process raw receipt text through parsing cascade
        
        Strategy:
        1. Try regex parser first (fast, deterministic)
        2. If confidence < threshold or failure, use GPT parser
        3. Apply operator mapping to normalize operator name
        4. Return fully structured transaction data
        
        Args:
            raw_text: Raw receipt text from Telegram
            
        Returns:
            Fully parsed transaction dict with all fields
        """
        if not raw_text or not raw_text.strip():
            return None
        
        parsed_data = None
        
        # Step 1: Try regex parser
        try:
            parsed_data = self.regex_parser.parse(raw_text)
            
            # Check if result meets confidence threshold
            if parsed_data and parsed_data.get('parsing_confidence', 0) >= self.confidence_threshold:
                print(f"✅ Regex parsing successful: {parsed_data['parsing_method']}")
            else:
                print(f"⚠️  Regex confidence too low or failed, falling back to GPT")
                parsed_data = None
        except Exception as e:
            print(f"❌ Regex parsing error: {e}")
            parsed_data = None
        
        # Step 2: Fallback to GPT if regex failed
        if not parsed_data:
            try:
                parsed_data = self.gpt_parser.parse(raw_text)
                if parsed_data:
                    print(f"✅ GPT parsing successful")
                else:
                    print(f"❌ GPT parsing also failed")
                    return None
            except Exception as e:
                print(f"❌ GPT parsing error: {e}")
                return None
        
        # Step 3: Apply operator mapping
        if parsed_data and parsed_data.get('operator_raw'):
            try:
                mapped_app = self.operator_mapper.map_operator(parsed_data['operator_raw'])
                parsed_data['application_mapped'] = mapped_app
                
                if mapped_app:
                    print(f"✅ Operator mapped: '{parsed_data['operator_raw']}' → '{mapped_app}'")
                else:
                    print(f"⚠️  No mapping found for operator: '{parsed_data['operator_raw']}'")
            except Exception as e:
                print(f"❌ Operator mapping error: {e}")
                parsed_data['application_mapped'] = None
        
        # Step 4: Mark GPT usage
        if parsed_data:
            parsed_data['is_gpt_parsed'] = (parsed_data.get('parsing_method') == 'GPT')
        
        return parsed_data
