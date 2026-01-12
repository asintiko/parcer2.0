"""
Celery worker for async receipt processing
Consumes from Redis queue and processes receipts
"""
import os
import asyncio
from celery import Celery
import redis
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Celery configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app = Celery('uzbek_parser_worker', broker=REDIS_URL, backend=REDIS_URL)

# Celery settings
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tashkent',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30,  # 30 seconds max per task
    worker_prefetch_multiplier=1,
)


@app.task(name='process_receipt', bind=True, max_retries=3)
def process_receipt_task(self, task_data_json: str):
    """
    Process a single receipt from the queue
    
    Args:
        task_data_json: JSON string containing receipt data
    """
    from database.connection import get_db
    from database.models import Transaction, ParsingLog
    from parsers.parser_orchestrator import ParserOrchestrator
    
    try:
        # Parse task data
        task_data = json.loads(task_data_json)
        raw_text = task_data['raw_text']
        source_type = task_data['source_type']
        source_chat_id = task_data['source_chat_id']
        source_message_id = task_data.get('source_message_id')
        
        start_time = datetime.now()
        
        # Process with parser orchestrator
        with get_db() as db:
            orchestrator = ParserOrchestrator(db)
            parsed_data = orchestrator.process(raw_text)
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if parsed_data:
                # Save to database
                transaction = Transaction(
                    raw_message=raw_text,
                    source_type=source_type,
                    source_chat_id=source_chat_id,
                    source_message_id=source_message_id,
                    transaction_date=parsed_data['transaction_date'],
                    amount=parsed_data['amount'],
                    currency=parsed_data.get('currency', 'UZS'),
                    card_last_4=parsed_data.get('card_last_4'),
                    operator_raw=parsed_data.get('operator_raw'),
                    application_mapped=parsed_data.get('application_mapped'),
                    transaction_type=parsed_data['transaction_type'],
                    balance_after=parsed_data.get('balance_after'),
                    is_gpt_parsed=parsed_data.get('is_gpt_parsed', False),
                    parsing_confidence=parsed_data.get('parsing_confidence'),
                    parsing_method=parsed_data.get('parsing_method')
                )
                db.add(transaction)
                db.commit()
                
                # Log success
                log = ParsingLog(
                    raw_message=raw_text,
                    parsing_method=parsed_data.get('parsing_method'),
                    success=True,
                    processing_time_ms=processing_time
                )
                db.add(log)
                db.commit()
                
                print(f"✅ Transaction saved: {transaction.id} ({transaction.amount} {transaction.currency})")
                
                return {
                    'success': True,
                    'transaction_id': transaction.id,
                    'amount': str(parsed_data['amount']),
                    'currency': parsed_data.get('currency'),
                    'application': parsed_data.get('application_mapped')
                }
            else:
                # Log failure
                log = ParsingLog(
                    raw_message=raw_text,
                    success=False,
                    error_message="Parsing returned None",
                    processing_time_ms=processing_time
                )
                db.add(log)
                db.commit()
                
                print(f"❌ Parsing failed for receipt")
                return {'success': False, 'error': 'Parsing failed'}
                
    except Exception as e:
        print(f"❌ Worker error: {e}")
        
        # Log exception
        try:
            with get_db() as db:
                log = ParsingLog(
                    raw_message=raw_text if 'raw_text' in locals() else '',
                    success=False,
                    error_message=str(e)
                )
                db.add(log)
                db.commit()
        except:
            pass
        
        # Retry task
        raise self.retry(exc=e, countdown=5)


# Redis queue consumer (alternative to Celery for simpler deployment)
class QueueConsumer:
    """Simple Redis queue consumer for processing receipts"""
    
    def __init__(self):
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    
    def start(self):
        """Start consuming from receipt_queue"""
        from database.connection import get_db
        from parsers.parser_orchestrator import ParserOrchestrator
        from database.models import Transaction, ParsingLog
        
        print("🔄 Queue consumer started, waiting for receipts...")
        
        while True:
            try:
                # Blocking pop from queue (timeout 1 second)
                result = self.redis_client.blpop('receipt_queue', timeout=1)
                
                if result:
                    queue_name, task_data_json = result
                    
                    # Process receipt
                    process_receipt_task(task_data_json)
                    
            except KeyboardInterrupt:
                print("\n👋 Queue consumer stopped")
                break
            except Exception as e:
                print(f"❌ Consumer error: {e}")
                continue


if __name__ == "__main__":
    # Run simple queue consumer instead of full Celery
    consumer = QueueConsumer()
    consumer.start()
