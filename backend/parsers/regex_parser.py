"""
Regex-based parser for Uzbek receipt formats
Handles three main formats: Humo Notification, SMS Inline, and Semicolon-delimited
"""
import re
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal
import pytz


class RegexParser:
    """Parser using regex patterns for structured receipt extraction"""
    
    def __init__(self, timezone: str = "Asia/Tashkent"):
        self.tz = pytz.timezone(timezone)
        
        # Regex patterns for different formats
        self.patterns = {
            'humo_notification': {
                'amount': r'[➖➕💸]\s*([\d\s\.,]+)\s*UZS',
                'transaction_type': r'(Оплата|Пополнение|Операция|Конверсия)',
                'card': r'(?:HUMO-?CARD|💳)\s*\*+(\d{4})',
                'operator': r'📍\s*(.+)',
                'datetime': r'[🕓🕘]\s*(\d{2}:\d{2})\s+(\d{2}\.\d{2}\.\d{2,4})',
                'balance': r'💰\s*([\d\s\.,]+)\s*UZS',
                'currency': r'(USD|UZS)',
            },
            'sms_inline': {
                'operator': r'(?:Pokupka|Spisanie c karty|Popolnenie scheta|E-Com oplata|Platezh):\s*(.+?)(?:,|\s+\d{2}\.\d{2})',
                'datetime': r'(\d{2}\.\d{2}\.\d{2})\s+(\d{2}:\d{2})',
                'amount': r'summa:([\d\.]+)\s*UZS',
                'card': r'karta\s*\*{3}(\d{4})',
                'balance': r'balans:([\d\.]+)\s*UZS',
                'type_keyword': r'^(Pokupka|Spisanie|Popolnenie|E-Com|Platezh|OTMENA)',
            },
            'semicolon_format': {
                'card_amount': r'HUMOCARD\s*\*(\d{4}):\s*(oplata|popolnenie|operacija)\s+([\d\.]+)\s*UZS',
                'operator': r';\s*([^;]+?)\s*;',
                'datetime': r';\s*(\d{2})-(\d{2})-(\d{2})\s+(\d{2}:\d{2})',
                'balance': r'Dostupno:\s*([\d\.]+)\s*UZS',
            }
        }
    
    def normalize_amount(self, amount_str: str) -> Decimal:
        """Normalize amount string to Decimal"""
        # Remove spaces and replace comma with dot
        cleaned = amount_str.replace(' ', '').replace(',', '.')
        return Decimal(cleaned)
    
    def parse_date(self, date_str: str, time_str: str, format_type: str = 'standard') -> datetime:
        """Parse date and time strings to datetime object"""
        try:
            if format_type == 'semicolon':
                # Format: YY-MM-DD HH:MM
                year, month, day = date_str.split('-')
                full_year = f"20{year}"
                dt_str = f"{full_year}-{month}-{day} {time_str}"
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            else:
                # Format: DD.MM.YYYY or DD.MM.YY
                parts = date_str.split('.')
                if len(parts[2]) == 2:
                    parts[2] = f"20{parts[2]}"
                dt_str = f"{parts[0]}.{parts[1]}.{parts[2]} {time_str}"
                dt = datetime.strptime(dt_str, "%d.%m.%Y %H:%M")
            
            # Localize to Tashkent timezone
            return self.tz.localize(dt)
        except Exception as e:
            raise ValueError(f"Date parsing error: {e}")
    
    def parse_humo_notification(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse Humo notification format (emoji-based, multi-line)"""
        patterns = self.patterns['humo_notification']
        
        # Extract amount
        amount_match = re.search(patterns['amount'], text)
        if not amount_match:
            return None
        amount = self.normalize_amount(amount_match.group(1))
        
        # Extract transaction type
        type_match = re.search(patterns['transaction_type'], text)
        if type_match:
            type_map = {
                'Оплата': 'DEBIT',
                'Пополнение': 'CREDIT',
                'Операция': 'DEBIT',
                'Конверсия': 'CONVERSION'
            }
            transaction_type = type_map.get(type_match.group(1), 'DEBIT')
        else:
            # Infer from emoji if no explicit type
            transaction_type = 'CREDIT' if '➕' in text or '🎉' in text else 'DEBIT'
        
        # Extract card
        card_match = re.search(patterns['card'], text)
        card_last_4 = card_match.group(1) if card_match else None
        
        # Extract operator
        operator_match = re.search(patterns['operator'], text)
        operator_raw = operator_match.group(1).strip() if operator_match else None
        
        # Extract datetime
        datetime_match = re.search(patterns['datetime'], text)
        if not datetime_match:
            return None
        time_str = datetime_match.group(1)
        date_str = datetime_match.group(2)
        transaction_date = self.parse_date(date_str, time_str)
        
        # Extract balance
        balance_match = re.search(patterns['balance'], text)
        balance_after = self.normalize_amount(balance_match.group(1)) if balance_match else None
        
        # Extract currency
        currency_match = re.search(patterns['currency'], text)
        currency = currency_match.group(1) if currency_match else 'UZS'
        
        return {
            'amount': amount,
            'currency': currency,
            'transaction_type': transaction_type,
            'card_last_4': card_last_4,
            'operator_raw': operator_raw,
            'transaction_date': transaction_date,
            'balance_after': balance_after,
            'parsing_method': 'REGEX_HUMO',
            'parsing_confidence': 0.95
        }
    
    def parse_sms_inline(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse SMS inline format (compact, comma-separated)"""
        patterns = self.patterns['sms_inline']
        
        # Extract amount
        amount_match = re.search(patterns['amount'], text)
        if not amount_match:
            return None
        amount = self.normalize_amount(amount_match.group(1))
        
        # Extract operator
        operator_match = re.search(patterns['operator'], text)
        operator_raw = operator_match.group(1).strip() if operator_match else None
        
        # Extract datetime
        datetime_match = re.search(patterns['datetime'], text)
        if not datetime_match:
            return None
        date_str = datetime_match.group(1)
        time_str = datetime_match.group(2)
        transaction_date = self.parse_date(date_str, time_str)
        
        # Extract card
        card_match = re.search(patterns['card'], text)
        card_last_4 = card_match.group(1) if card_match else None
        
        # Extract balance
        balance_match = re.search(patterns['balance'], text)
        balance_after = self.normalize_amount(balance_match.group(1)) if balance_match else None
        
        # Determine transaction type
        type_match = re.search(patterns['type_keyword'], text)
        if type_match:
            keyword = type_match.group(1)
            if keyword in ['Popolnenie']:
                transaction_type = 'CREDIT'
            elif keyword == 'OTMENA':
                transaction_type = 'REVERSAL'
            else:
                transaction_type = 'DEBIT'
        else:
            transaction_type = 'DEBIT'
        
        return {
            'amount': amount,
            'currency': 'UZS',
            'transaction_type': transaction_type,
            'card_last_4': card_last_4,
            'operator_raw': operator_raw,
            'transaction_date': transaction_date,
            'balance_after': balance_after,
            'parsing_method': 'REGEX_SMS',
            'parsing_confidence': 0.90
        }
    
    def parse_semicolon_format(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse semicolon-delimited format (HUMOCARD *6921: ...)"""
        patterns = self.patterns['semicolon_format']
        
        # Extract card, type, and amount
        card_amount_match = re.search(patterns['card_amount'], text)
        if not card_amount_match:
            return None
        
        card_last_4 = card_amount_match.group(1)
        op_type = card_amount_match.group(2)
        amount = self.normalize_amount(card_amount_match.group(3))
        
        # Map operation type
        type_map = {'oplata': 'DEBIT', 'popolnenie': 'CREDIT', 'operacija': 'DEBIT'}
        transaction_type = type_map.get(op_type, 'DEBIT')
        
        # Extract operator
        operator_match = re.search(patterns['operator'], text)
        operator_raw = operator_match.group(1).strip() if operator_match else None
        
        # Extract datetime (YY-MM-DD format)
        datetime_match = re.search(patterns['datetime'], text)
        if not datetime_match:
            return None
        
        year = datetime_match.group(1)
        month = datetime_match.group(2)
        day = datetime_match.group(3)
        time_str = datetime_match.group(4)
        date_str = f"{year}-{month}-{day}"
        
        transaction_date = self.parse_date(date_str, time_str, format_type='semicolon')
        
        # Extract balance
        balance_match = re.search(patterns['balance'], text)
        balance_after = self.normalize_amount(balance_match.group(1)) if balance_match else None
        
        return {
            'amount': amount,
            'currency': 'UZS',
            'transaction_type': transaction_type,
            'card_last_4': card_last_4,
            'operator_raw': operator_raw,
            'transaction_date': transaction_date,
            'balance_after': balance_after,
            'parsing_method': 'REGEX_SEMICOLON',
            'parsing_confidence': 0.92
        }
    
    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Main parse method - tries all formats in cascade
        
        Args:
            text: Raw receipt text
            
        Returns:
            Parsed transaction dict or None if parsing failed
        """
        # Try Humo notification format first (most common)
        if any(emoji in text for emoji in ['💸', '💳', '📍', '🕓', '🕘']):
            result = self.parse_humo_notification(text)
            if result:
                return result
        
        # Try semicolon format
        if 'HUMOCARD *' in text and ';' in text:
            result = self.parse_semicolon_format(text)
            if result:
                return result
        
        # Try SMS inline format
        if 'summa:' in text and 'karta' in text:
            result = self.parse_sms_inline(text)
            if result:
                return result
        
        # All formats failed
        return None
