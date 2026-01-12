"""
GPT-4o parser using OpenAI Structured Outputs
Fallback parser for complex or irregular receipt formats
"""
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
import os
import json
from openai import OpenAI
from pydantic import BaseModel, Field
import pytz


class TransactionSchema(BaseModel):
    """Structured output schema for GPT parsing"""
    amount: float = Field(description="Transaction amount as a number")
    currency: str = Field(default="UZS", description="Currency code (UZS, USD, etc.)")
    transaction_date_iso: str = Field(description="Transaction date and time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)")
    card_last_4: Optional[str] = Field(None, description="Last 4 digits of card number")
    operator_raw: Optional[str] = Field(None, description="Raw operator/merchant name from receipt")
    transaction_type: str = Field(description="Transaction type: DEBIT, CREDIT, CONVERSION, or REVERSAL")
    balance_after: Optional[float] = Field(None, description="Account balance after transaction")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")


class GPTParser:
    """Parser using OpenAI GPT-4o with Structured Outputs"""
    
    def __init__(self, api_key: Optional[str] = None, timezone: str = "Asia/Tashkent"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.api_key)
        self.tz = pytz.timezone(timezone)
        
        self.system_prompt = """You are a financial data analyst specialized in Uzbek payment systems.

Your task is to analyze receipt text from Uzbek banks and payment systems (Uzcard, Humo, Click, Payme, etc.) and extract structured transaction data.

Context:
- Amounts are typically in UZS (Uzbek Som), sometimes in USD
- Dates follow DD.MM.YYYY or YY-MM-DD formats
- 'Operator' refers to the payment gateway or merchant (e.g., Payme, Click, Paynet, NBU, SmartBank)
- Card numbers are shown as last 4 digits with asterisks (e.g., ***6714 or *6714)
- Transaction types:
  * DEBIT: Payments, purchases, withdrawals (Оплата, Pokupka, Spisanie)
  * CREDIT: Deposits, refunds (Пополнение, Popolnenie)
  * CONVERSION: Currency exchange (Конверсия)
  * REVERSAL: Cancellation (OTMENA)

Extract all available fields with high confidence. If a field is not present, return null.
For dates, convert to ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
Provide a confidence score based on data clarity."""
    
    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse receipt using GPT-4o with Structured Outputs
        
        Args:
            text: Raw receipt text
            
        Returns:
            Parsed transaction dict or None if parsing failed
        """
        try:
            # Call GPT-4o with structured outputs
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Parse this Uzbek financial receipt:\n\n{text}"}
                ],
                response_format=TransactionSchema,
                temperature=0.1  # Low temperature for deterministic output
            )
            
            # Extract parsed data
            parsed = response.choices[0].message.parsed
            
            if not parsed:
                return None
            
            # Convert to our internal format
            # Parse ISO datetime
            transaction_date = datetime.fromisoformat(parsed.transaction_date_iso.replace('Z', '+00:00'))
            
            # Ensure timezone is Tashkent
            if transaction_date.tzinfo is None:
                transaction_date = self.tz.localize(transaction_date)
            else:
                transaction_date = transaction_date.astimezone(self.tz)
            
            result = {
                'amount': Decimal(str(parsed.amount)),
                'currency': parsed.currency,
                'transaction_type': parsed.transaction_type,
                'card_last_4': parsed.card_last_4,
                'operator_raw': parsed.operator_raw,
                'transaction_date': transaction_date,
                'balance_after': Decimal(str(parsed.balance_after)) if parsed.balance_after else None,
                'parsing_method': 'GPT',
                'parsing_confidence': parsed.confidence
            }
            
            return result
            
        except Exception as e:
            print(f"❌ GPT parsing error: {e}")
            return None
