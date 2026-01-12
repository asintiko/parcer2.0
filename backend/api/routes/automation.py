"""
API Routes for AI-powered Transaction Automation
Analyzes transactions and suggests application mappings using OpenAI
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime
import asyncio
from openai import AsyncOpenAI
import os
import json
import httpx
from bs4 import BeautifulSoup

from database.connection import get_db_session
from database.models import Check, OperatorReference

router = APIRouter(prefix="/api/automation", tags=["automation"])

# OpenAI Client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Request/Response Models
class AnalyzeRequest(BaseModel):
    limit: Optional[int] = Field(default=100, ge=1, le=1000)
    only_unmapped: bool = True
    currency_filter: Optional[str] = None  # UZS, USD, or None for all


class AISuggestion(BaseModel):
    application: str
    confidence: float
    is_new: bool
    is_p2p: bool
    reasoning: str


class SuggestionResponse(BaseModel):
    id: str
    transaction_id: str
    operator_raw: str
    current_application: Optional[str]
    suggested_application: str
    confidence: float
    reasoning: str
    is_new_application: bool
    is_p2p: bool
    status: str
    created_at: datetime


class AnalyzeResponse(BaseModel):
    task_id: str
    status: str
    message: str


class AnalyzeStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: dict
    results: Optional[dict] = None


# In-memory task storage (replace with Redis in production)
tasks_storage = {}


def get_existing_applications(db: Session) -> List[str]:
    """Get list of existing applications from OperatorReference"""
    apps = db.query(OperatorReference.application_name)\
        .distinct()\
        .filter(OperatorReference.is_active == True)\
        .all()
    return [app[0] for app in apps if app[0]]


async def search_web_for_operator(operator_raw: str) -> str:
    """Search the web for information about the operator"""
    try:
        # Search query
        search_query = f"{operator_raw} Узбекистан приложение оплата"

        # Use DuckDuckGo HTML search (no API key needed)
        url = f"https://html.duckduckgo.com/html/?q={httpx.QueryParams({'q': search_query})}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": search_query},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract snippets from search results
                snippets = []
                results = soup.find_all('a', class_='result__snippet', limit=3)

                for result in results:
                    text = result.get_text(strip=True)
                    if text and len(text) > 20:
                        snippets.append(text)

                if snippets:
                    return "\n".join(snippets[:3])  # Top 3 results

        return "Информация не найдена"

    except Exception as e:
        print(f"Web search error: {e}")
        return "Ошибка поиска"


async def analyze_with_ai(
    operator_raw: str,
    existing_apps: List[str],
    transaction_context: dict = None,
    web_search_enabled: bool = True
) -> AISuggestion:
    """Use OpenAI to suggest application mapping with optional web search"""

    # Perform web search if enabled
    web_info = ""
    if web_search_enabled:
        web_info = await search_web_for_operator(operator_raw)

    system_prompt = """Ты эксперт по финансовым транзакциям в Узбекистане.
Твоя задача - определить к какому приложению/сервису относится оператор транзакции и является ли это P2P переводом.

Существующие приложения в системе:
{apps_list}

Правила:
1. Если оператор явно относится к существующему приложению - выбери его
2. Если это новый оператор/сервис - предложи новое название
3. Определи, является ли это P2P переводом (перевод между физическими лицами):
   - P2P (is_p2p=true): переводы по номеру телефона, по имени человека, "Перевод другу", имена людей
   - НЕ P2P (is_p2p=false): оплата услуг, покупки в магазинах, операторы связи, коммунальные услуги
4. Для узбекских сервисов сохраняй оригинальные названия
5. Будь консервативен - если не уверен, укажи низкую уверенность

Ответь в JSON формате:
{{
    "application": "название приложения",
    "confidence": 0.95,
    "is_new": false,
    "is_p2p": false,
    "reasoning": "краткое объяснение"
}}"""

    web_context = f"\n\nИнформация из интернета:\n{web_info}" if web_info and web_info != "Информация не найдена" and web_info != "Ошибка поиска" else ""

    user_prompt = f"""Оператор: "{operator_raw}"

Контекст транзакции:
- Тип: {transaction_context.get('transaction_type', 'N/A') if transaction_context else 'N/A'}
- Сумма: {transaction_context.get('amount', 'N/A') if transaction_context else 'N/A'}
- Дата: {transaction_context.get('date', 'N/A') if transaction_context else 'N/A'}{web_context}

Определи приложение и P2P статус."""

    apps_list = "\n".join(f"- {app}" for app in existing_apps) if existing_apps else "Нет существующих приложений"

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # Используем более дешевую модель
            messages=[
                {"role": "system", "content": system_prompt.format(apps_list=apps_list)},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=200
        )

        result = json.loads(response.choices[0].message.content)
        return AISuggestion(**result)

    except Exception as e:
        print(f"OpenAI API Error: {e}")
        # Fallback suggestion
        return AISuggestion(
            application="Unknown",
            confidence=0.0,
            is_new=True,
            is_p2p=False,
            reasoning=f"Error: {str(e)}"
        )


async def process_transactions_batch(
    db: Session,
    transactions: List[Check],
    task_id: str
):
    """Process batch of transactions with AI analysis"""

    # Get existing applications
    existing_apps = get_existing_applications(db)

    total = len(transactions)
    processed = 0
    suggestions = []

    # Update task status
    tasks_storage[task_id]["status"] = "processing"
    tasks_storage[task_id]["progress"] = {
        "total": total,
        "processed": 0,
        "percent": 0
    }

    for transaction in transactions:
        try:
            # Check if already has good mapping
            if transaction.app and transaction.app in existing_apps:
                processed += 1
                continue

            # Analyze with AI
            context = {
                "transaction_type": transaction.transaction_type,
                "amount": str(transaction.amount) if transaction.amount else None,
                "date": transaction.datetime.isoformat() if transaction.datetime else None
            }

            ai_result = await analyze_with_ai(
                transaction.operator or "Unknown",
                existing_apps,
                context
            )

            # Store suggestion (in production, save to ai_suggestions table)
            suggestion = {
                "id": str(uuid4()),
                "transaction_id": str(transaction.id),
                "operator_raw": transaction.operator,
                "current_application": transaction.app,
                "suggested_application": ai_result.application,
                "confidence": ai_result.confidence,
                "reasoning": ai_result.reasoning,
                "is_new_application": ai_result.is_new,
                "is_p2p": ai_result.is_p2p,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat()
            }

            suggestions.append(suggestion)
            processed += 1

            # Update progress
            tasks_storage[task_id]["progress"] = {
                "total": total,
                "processed": processed,
                "percent": round((processed / total) * 100, 1)
            }

            # Rate limiting - не перегружаем API
            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"Error processing transaction {transaction.id}: {e}")
            processed += 1
            continue

    # Complete task
    high_confidence = len([s for s in suggestions if s["confidence"] >= 0.8])
    low_confidence = len([s for s in suggestions if s["confidence"] < 0.8])

    tasks_storage[task_id]["status"] = "completed"
    tasks_storage[task_id]["suggestions"] = suggestions
    tasks_storage[task_id]["results"] = {
        "suggestions_count": len(suggestions),
        "high_confidence": high_confidence,
        "low_confidence": low_confidence
    }


@router.post("/analyze-transactions", response_model=AnalyzeResponse)
async def analyze_transactions(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session)
):
    """Start AI analysis of transactions"""

    # Build query
    query = db.query(Check)

    if request.only_unmapped:
        query = query.filter(
            (Check.app == None) |
            (Check.app == "")
        )

    if request.currency_filter:
        query = query.filter(Check.currency == request.currency_filter)

    query = query.order_by(Check.datetime.desc()).limit(request.limit)

    transactions = query.all()

    if not transactions:
        raise HTTPException(status_code=404, detail="No transactions found for analysis")

    # Create task
    task_id = str(uuid4())
    tasks_storage[task_id] = {
        "task_id": task_id,
        "status": "started",
        "created_at": datetime.utcnow().isoformat(),
        "progress": {"total": 0, "processed": 0, "percent": 0},
        "results": None,
        "suggestions": []
    }

    # Start background processing
    background_tasks.add_task(process_transactions_batch, db, transactions, task_id)

    return AnalyzeResponse(
        task_id=task_id,
        status="started",
        message=f"Analysis started for {len(transactions)} transactions"
    )


@router.get("/analyze-status/{task_id}", response_model=AnalyzeStatusResponse)
async def get_analyze_status(task_id: str):
    """Get status of AI analysis task"""

    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks_storage[task_id]

    return AnalyzeStatusResponse(
        task_id=task["task_id"],
        status=task["status"],
        progress=task["progress"],
        results=task.get("results")
    )


@router.get("/suggestions", response_model=List[SuggestionResponse])
async def get_suggestions(
    status: Optional[str] = "pending",
    confidence_min: Optional[float] = 0.0,
    task_id: Optional[str] = None
):
    """Get AI suggestions for review"""

    all_suggestions = []

    # Collect suggestions from all completed tasks
    for tid, task in tasks_storage.items():
        if task_id and tid != task_id:
            continue

        if task["status"] in ["completed", "processing"]:
            for sug in task.get("suggestions", []):
                if status and sug["status"] != status:
                    continue
                if sug["confidence"] < confidence_min:
                    continue

                all_suggestions.append(SuggestionResponse(**sug))

    return all_suggestions


@router.post("/suggestions/{suggestion_id}/apply")
async def apply_suggestion(
    suggestion_id: str,
    db: Session = Depends(get_db_session)
):
    """Apply AI suggestion to transaction"""

    # Find suggestion across all tasks
    suggestion = None
    for task in tasks_storage.values():
        for sug in task.get("suggestions", []):
            if sug["id"] == suggestion_id:
                suggestion = sug
                break
        if suggestion:
            break

    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    # Update transaction
    transaction = db.query(Check).filter(Check.id == int(suggestion["transaction_id"])).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    transaction.app = suggestion["suggested_application"]
    transaction.is_p2p = suggestion["is_p2p"]
    db.commit()

    # Update suggestion status
    suggestion["status"] = "approved"

    return {"success": True, "transaction_id": suggestion["transaction_id"]}


@router.post("/suggestions/{suggestion_id}/reject")
async def reject_suggestion(suggestion_id: str):
    """Reject AI suggestion"""

    # Find and update suggestion
    for task in tasks_storage.values():
        for sug in task.get("suggestions", []):
            if sug["id"] == suggestion_id:
                sug["status"] = "rejected"
                return {"success": True}

    raise HTTPException(status_code=404, detail="Suggestion not found")


@router.post("/suggestions/batch-apply")
async def batch_apply_suggestions(
    suggestion_ids: List[str],
    db: Session = Depends(get_db_session)
):
    """Apply multiple suggestions at once"""

    applied = 0
    errors = []

    for sug_id in suggestion_ids:
        try:
            await apply_suggestion(sug_id, db)
            applied += 1
        except Exception as e:
            errors.append({"suggestion_id": sug_id, "error": str(e)})

    return {
        "success": True,
        "applied": applied,
        "errors": errors
    }
