"""
One-time maintenance script to normalize Check source and transaction_type values safely.

Rules:
- Skip rows where added_via indicates manual entry.
- Source:
    Manual if added_via is manual
    Telegram if raw_text contains emoji in U+1F300–U+1FAFF or U+2600–U+27BF
    SMS otherwise
- Transaction type (only when raw_text provides explicit evidence):
    REVERSAL  : contains OTMENA / ОТМЕНА
    CONVERSION: contains Конверсия / CONVERSION / KONVERS
    CREDIT    : contains ➕ or Popolnenie / KIRIM / Пополнение
    DEBIT     : contains ➖ or Oplata / Pokupka / Platezh / Spisanie / E-Com
    Priority: REVERSAL > CONVERSION > explicit sign > keyword mapping
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from typing import Optional

from sqlalchemy.orm import Session

from database.connection import get_db_session
from database.models import Check

BATCH_SIZE = 1000

# Emoji range covering U+1F300–U+1FAFF and U+2600–U+27BF
EMOJI_PATTERN = re.compile(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]")

REVERSAL_KEYWORDS = ("ОТМЕНА", "OTMENA")
CONVERSION_KEYWORDS = ("КОНВЕРС", "CONVERSION", "KONVERS")
CREDIT_KEYWORDS = ("ПОПОЛНЕНИЕ", "POPOLNENIE", "KIRIM")
DEBIT_KEYWORDS = ("ОПЛАТА", "OPLATA", "POKUPKA", "PLATEZH", "SPISANIE", "E-COM")


@contextmanager
def session_from_dependency() -> Session:
    """
    Helper to reuse get_db_session (FastAPI dependency) in a script context.
    """
    gen = get_db_session()
    session = next(gen)
    try:
        yield session
    finally:
        try:
            gen.close()
        finally:
            session.close()


def infer_source(added_via: Optional[str], raw_text: Optional[str]) -> str:
    if added_via and added_via.strip().lower() == "manual":
        return "Manual"
    if raw_text and EMOJI_PATTERN.search(raw_text):
        return "Telegram"
    return "SMS"


def infer_transaction_type_from_text(raw_text: Optional[str]) -> Optional[str]:
    if not raw_text:
        return None

    text_upper = raw_text.upper()

    if any(keyword in text_upper for keyword in REVERSAL_KEYWORDS):
        return "REVERSAL"

    if any(keyword in text_upper for keyword in CONVERSION_KEYWORDS):
        return "CONVERSION"

    if "➕" in raw_text:
        return "CREDIT"
    if "➖" in raw_text:
        return "DEBIT"

    if any(keyword in text_upper for keyword in CREDIT_KEYWORDS):
        return "CREDIT"

    if any(keyword in text_upper for keyword in DEBIT_KEYWORDS):
        return "DEBIT"

    return None


def normalize_checks(batch_size: int = BATCH_SIZE) -> None:
    updated_source_count = 0
    updated_type_count = 0
    skipped_manual_count = 0
    processed_total = 0
    pending_changes = 0

    with session_from_dependency() as session:
        query = session.query(Check).order_by(Check.id)

        for check in query.yield_per(batch_size):
            processed_total += 1

            added_via = (check.added_via or "").lower()
            if "manual" in added_via:
                skipped_manual_count += 1
                continue

            desired_source = infer_source(check.added_via, check.raw_text)
            if check.source != desired_source:
                check.source = desired_source
                updated_source_count += 1
                pending_changes += 1

            inferred_type = infer_transaction_type_from_text(check.raw_text)
            if inferred_type and inferred_type != check.transaction_type:
                check.transaction_type = inferred_type
                updated_type_count += 1
                pending_changes += 1

            if pending_changes and pending_changes % batch_size == 0:
                session.commit()
                pending_changes = 0

        if pending_changes:
            session.commit()

    print("Normalization complete:")
    print(f"  processed_total      : {processed_total}")
    print(f"  skipped_manual_count : {skipped_manual_count}")
    print(f"  updated_source_count : {updated_source_count}")
    print(f"  updated_type_count   : {updated_type_count}")


if __name__ == "__main__":
    normalize_checks()
