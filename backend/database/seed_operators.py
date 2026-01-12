"""
Seed operator mappings from reference file into database
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db
from database.models import OperatorMapping


# Mapping data extracted from операторыпродавцыиприложения-2.txt
OPERATOR_MAPPINGS = [
    # Milliy 2.0
    ("NBU 2P2", "Milliy 2.0", 10),
    ("NBU P2P HUMO UZCARD", "Milliy 2.0", 10),
    ("NBU P2P HUMOHUMO", "Milliy 2.0", 10),
    ("NBU P2P UZCARD HUMO", "Milliy 2.0", 10),
    ("NBU P2P", "Milliy 2.0", 5),
    ("NBU ONLINE", "Milliy 2.0", 5),
    ("MILLIY", "Milliy 2.0", 3),
    
    # MyUztelecom
    ("PSP P2P AKSIYA", "MyUztelecom", 10),
    ("PSP P2P HUMO2UZCARD", "MyUztelecom", 10),
    ("MYUZTELECOM", "MyUztelecom", 5),
    
    # Humans
    ("UPAY P2P", "Humans", 10),
    ("UPAY HUMO2UZCARD", "Humans", 10),
    ("UPAY UZCARD2HUMO", "Humans", 10),
    ("UPAY HUMO2HUMO", "Humans", 10),
    ("DAVR UPAY HUMANS", "Humans", 15),
    ("UPAY", "Humans", 5),
    ("HUMANS", "Humans", 3),
    
    # Tenge24
    ("TENGE UNIVERSAL P2P", "Tenge24", 10),
    ("T24 P2P", "Tenge24", 10),
    ("NEW DBO UZKART-HUMO", "Tenge24", 10),
    ("TENGE 24 P2P", "Tenge24", 10),
    ("TENGE-24 WS P2P", "Tenge24", 10),
    ("TENGE24 WS P2P", "Tenge24", 10),
    ("TENGE", "Tenge24", 5),
    ("T24", "Tenge24", 5),
    
    # Xazna
    ("XAZNA OTHERS", "Xazna", 10),
    ("XAZNA HUMO 2 UZCARD", "Xazna", 10),
    ("XAZNA P2P", "Xazna", 10),
    ("XAZNA PAYNET", "Xazna", 10),
    ("XAZNA", "Xazna", 5),
    
    # Davr Mobile
    ("DAVR MOBILE UZCARD", "Davr Mobile", 10),
    ("DAVR MOBILE P2P", "Davr Mobile", 10),
    ("DAVR MOBILE HUMO", "Davr Mobile", 10),
    ("DAVR MOBILE", "Davr Mobile", 5),
    
    # Hamkor
    ("HAMKORBANK ATB", "Hamkor", 10),
    ("HAMKOR P2P", "Hamkor", 10),
    ("HAMKOR HUMO P2P", "Hamkor", 10),
    ("HAMKOR", "Hamkor", 5),
    
    # OQ
    ("OQ P2P", "OQ", 10),
    
    # Paynet
    ("AT KHALK BANKI", "Paynet", 10),
    ("UZPAYNET", "Paynet", 10),
    ("PAYNET HUM2UZC", "Paynet", 10),
    ("PAYNET P2P", "Paynet", 10),
    ("UZCARD OTHERS 2 ANY PAYNET", "Paynet", 15),
    ("PAYNET", "Paynet", 5),
    
    # Mavrid
    ("MIKROKREDITBANK ATB", "Mavrid", 10),
    ("MKBANK MAVRID", "Mavrid", 10),
    ("MKBANK P2P UZCARD MAVRID", "Mavrid", 10),
    ("MAVRID", "Mavrid", 5),
    
    # Joyda
    ("UZCARD PLYUS P2P", "Joyda", 10),
    ("JOYDA", "Joyda", 5),
    
    # Agrobank
    ("UZCARD P2P", "Agrobank", 8),
    ("AGROBANK", "Agrobank", 5),
    
    # Asakabank
    ("ASAKABANK HUMO UZCAR", "Asakabank", 10),
    ("ASAKA AT BANKINING", "Asakabank", 10),
    ("ASAKABANK UZCARD HUMO", "Asakabank", 10),
    ("ASAKA HUMO UZCARD", "Asakabank", 10),
    ("ASAKABANK", "Asakabank", 5),
    ("ASAKA", "Asakabank", 3),
    
    # SmartBank
    ("SMARTBANK P2P O2O UZCARD", "SmartBank", 10),
    ("SMARTBANK UZCARD HUMO", "SmartBank", 10),
    ("SmartBank P2P", "SmartBank", 10),
    ("SMARTBANK", "SmartBank", 5),
    
    # Beepul
    ("BEEPUL UZCARD 2 UZCARD", "Beepul", 10),
    ("BEEPUL UZCARD 2 HUMO", "Beepul", 10),
    ("BEEPUL", "Beepul", 5),
    
    # PayWay
    ("PAYWAY", "PayWay", 10),
    
    # Payme
    ("PAYME P2P", "Payme", 10),
    ("PAYME OPLATA", "Payme", 10),
    ("PL HUMANS OPLATA", "Payme", 10),
    ("PAYME", "Payme", 5),
    
    # UzumBank
    ("UB PEREVOD", "UzumBank", 10),
    ("UZUMBANK", "UzumBank", 5),
    
    # SQB / Chakanapay
    ("SQB MOBILE UZCARD P2P", "SQB", 10),
    ("SQB MOBILE HUMO P2P", "SQB", 10),
    ("SQB", "SQB", 5),
    ("CHAKANAPAY UZCARD", "Chakanapay", 10),
    ("ChakanaPay Humo", "Chakanapay", 10),
    ("CHAKANAPAY", "Chakanapay", 5),
]


def seed_operators():
    """Seed operator mappings into database"""
    with get_db() as db:
        # Clear existing mappings
        db.query(OperatorMapping).delete()
        db.commit()
        
        # Insert new mappings
        for pattern, app_name, priority in OPERATOR_MAPPINGS:
            mapping = OperatorMapping(
                pattern=pattern.upper(),  # Normalize to uppercase
                app_name=app_name,
                priority=priority,
                is_active=True
            )
            db.add(mapping)
        
        db.commit()
        print(f"✅ Successfully seeded {len(OPERATOR_MAPPINGS)} operator mappings")


if __name__ == "__main__":
    seed_operators()
