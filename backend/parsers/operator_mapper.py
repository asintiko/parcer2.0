"""
Operator name to application mapping module
Maps raw operator strings to user-friendly application names
"""
from typing import Optional
import re
from sqlalchemy.orm import Session
from database.models import OperatorMapping


class OperatorMapper:
    """Maps raw operator names to application names using fuzzy matching"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.mappings_cache = None
        self._load_mappings()
    
    def _load_mappings(self):
        """Load operator mappings from database and cache"""
        mappings = self.db_session.query(OperatorMapping).filter(
            OperatorMapping.is_active == True
        ).order_by(OperatorMapping.priority.desc()).all()
        
        self.mappings_cache = [
            (m.pattern, m.app_name, m.priority) for m in mappings
        ]
    
    def normalize_operator(self, operator_str: str) -> str:
        """Normalize operator string for matching"""
        if not operator_str:
            return ""
        
        # Convert to uppercase
        normalized = operator_str.upper()
        
        # Remove excessive whitespace
        normalized = ' '.join(normalized.split())
        
        # Remove some special characters but keep important ones
        # Keep: letters, digits, spaces, >, <, 2, P2P patterns
        normalized = re.sub(r'[^\w\s><]', ' ', normalized)
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def map_operator(self, operator_raw: str) -> Optional[str]:
        """
        Map raw operator string to application name
        
        Args:
            operator_raw: Raw operator string from receipt
            
        Returns:
            Mapped application name or None if no match found
        """
        if not operator_raw:
            return None
        
        # Normalize input
        normalized_input = self.normalize_operator(operator_raw)
        
        # Try exact match first
        for pattern, app_name, _ in self.mappings_cache:
            if pattern == normalized_input:
                return app_name
        
        # Try substring matching (ordered by priority)
        best_match = None
        best_priority = -1
        
        for pattern, app_name, priority in self.mappings_cache:
            # Check if pattern is contained in normalized input
            if pattern in normalized_input:
                if priority > best_priority:
                    best_match = app_name
                    best_priority = priority
        
        return best_match
    
    def refresh_cache(self):
        """Refresh mappings cache from database"""
        self._load_mappings()
