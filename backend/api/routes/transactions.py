"""
Transaction API routes
CRUD operations for financial transactions
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from decimal import Decimal

from database.connection import get_db_session
from database.models import Transaction, Check

router = APIRouter()


# Pydantic schemas
class TransactionResponse(BaseModel):
    id: int
    transaction_date: datetime
    amount: str
    currency: str
    card_last_4: Optional[str]
    operator_raw: Optional[str]
    application_mapped: Optional[str]
    transaction_type: str
    balance_after: Optional[str]
    source_type: str
    parsing_method: Optional[str]
    parsing_confidence: Optional[float]
    is_p2p: Optional[bool]  # Added for P2P transactions
    created_at: datetime
    
    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    transactions: List[TransactionResponse]


# Update/Delete schemas
class CheckUpdateRequest(BaseModel):
    """Schema for updating check fields"""
    datetime: Optional[datetime] = None
    operator: Optional[str] = Field(None, max_length=255)
    app: Optional[str] = Field(None, max_length=100)
    amount: Optional[Decimal] = Field(None, ge=0)
    balance: Optional[Decimal] = None
    card_last4: Optional[str] = Field(None, pattern=r'^\d{4}$')
    is_p2p: Optional[bool] = None
    transaction_type: Optional[str] = Field(None, pattern=r'^(DEBIT|CREDIT|CONVERSION|REVERSAL)$')
    currency: Optional[str] = Field(None, pattern=r'^(UZS|USD)$')
    source: Optional[str] = Field(None, pattern=r'^(auto|manual)$')

    class Config:
        json_schema_extra = {
            "example": {
                "operator": "Updated Operator Name",
                "amount": "150000.00",
                "is_p2p": True
            }
        }


class CheckUpdateResponse(BaseModel):
    """Response after successful update"""
    success: bool
    message: str
    check: TransactionResponse


class DeleteResponse(BaseModel):
    """Response after deletion"""
    success: bool
    message: str
    deleted_id: int


class BulkDeleteRequest(BaseModel):
    """Schema for bulk delete operations"""
    ids: List[int] = Field(..., min_length=1, max_length=100)


class BulkDeleteResponse(BaseModel):
    """Response for bulk delete"""
    success: bool
    deleted_count: int
    failed_ids: List[int] = []
    errors: List[str] = []


@router.get("/", response_model=TransactionListResponse)
async def get_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    card: Optional[str] = Query(None, description="Filter by last 4 digits of card"),
    app: Optional[str] = Query(None, description="Filter by application name"),
    start_date: Optional[datetime] = Query(None, description="Filter transactions from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter transactions until this date"),
    transaction_type: Optional[str] = Query(None, description="Filter by type: DEBIT, CREDIT, CONVERSION, REVERSAL"),
    db: Session = Depends(get_db_session)
):
    """
    Get paginated list of checks (transactions) with filters
    
    - **page**: Page number (starts from 1)
    - **page_size**: Number of items per page (max 200)
    - **card**: Filter by card last 4 digits
    - **app**: Filter by application name
    - **start_date**: From date (ISO format)
    - **end_date**: To date (ISO format)
    - **transaction_type**: Filter by transaction type
    """
    try:
        # Build query using Check model
        query = db.query(Check)
        
        # Apply filters
        if card:
            query = query.filter(Check.card_last4 == card)
        
        if app:
            query = query.filter(Check.app == app)
        
        if start_date:
            query = query.filter(Check.datetime >= start_date)
        
        if end_date:
            query = query.filter(Check.datetime <= end_date)
        
        if transaction_type:
            query = query.filter(Check.transaction_type == transaction_type)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering (from oldest to newest)
        offset = (page - 1) * page_size
        checks = query.order_by(Check.datetime.asc()).offset(offset).limit(page_size).all()
        
        # Convert Check to TransactionResponse format
        transaction_responses = [
            TransactionResponse(
                id=c.id,
                transaction_date=c.datetime,
                amount=str(c.amount),
                currency=c.currency,
                card_last_4=c.card_last4,
                operator_raw=c.operator,
                application_mapped=c.app,
                transaction_type=c.transaction_type,
                balance_after=str(c.balance) if c.balance else None,
                source_type=c.source.upper() if c.source else 'MANUAL',  # Map to MANUAL/AUTO
                parsing_method=c.added_via,
                parsing_confidence=None,  # Not available in checks table
                is_p2p=c.is_p2p,
                created_at=c.created_at
            ) for c in checks
        ]
        
        return TransactionListResponse(
            total=total,
            page=page,
            page_size=page_size,
            transactions=transaction_responses
        )
    
    finally:
        db.close()


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db_session)
):
    """Get single check (transaction) by ID"""
    try:
        check = db.query(Check).filter(Check.id == transaction_id).first()
        
        if not check:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return TransactionResponse(
            id=check.id,
            transaction_date=check.datetime,
            amount=str(check.amount),
            currency=check.currency,
            card_last_4=check.card_last4,
            operator_raw=check.operator,
            application_mapped=check.app,
            transaction_type=check.transaction_type,
            balance_after=str(check.balance) if check.balance else None,
            source_type=check.source.upper() if check.source else 'MANUAL',
            parsing_method=check.added_via,
            parsing_confidence=None,
            is_p2p=check.is_p2p,
            created_at=check.created_at
        )
    finally:
        db.close()


@router.put("/{transaction_id}", response_model=CheckUpdateResponse)
async def update_transaction(
    transaction_id: int,
    update_data: CheckUpdateRequest,
    db: Session = Depends(get_db_session)
):
    """
    Update a check (transaction) by ID

    Only provided fields will be updated (partial update).
    - **transaction_id**: ID of check to update
    - **update_data**: Fields to update (all optional)

    Returns updated check data.
    """
    try:
        # Find check
        check = db.query(Check).filter(Check.id == transaction_id).first()

        if not check:
            raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")

        # Apply updates (only non-None fields)
        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            if value is not None:
                setattr(check, field, value)

        # Update metadata
        check.updated_at = func.now()

        # Recalculate weekday and display fields if datetime changed
        if update_data.datetime:
            days = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб']
            check.weekday = days[update_data.datetime.weekday()]
            check.date_display = update_data.datetime.strftime('%d.%m.%Y')
            check.time_display = update_data.datetime.strftime('%H:%M')

        # Commit changes
        db.commit()
        db.refresh(check)

        # Convert to response format
        response_check = TransactionResponse(
            id=check.id,
            transaction_date=check.datetime,
            amount=str(check.amount),
            currency=check.currency,
            card_last_4=check.card_last4,
            operator_raw=check.operator,
            application_mapped=check.app,
            transaction_type=check.transaction_type,
            balance_after=str(check.balance) if check.balance else None,
            source_type=check.source.upper() if check.source else 'MANUAL',
            parsing_method=check.added_via,
            parsing_confidence=None,
            is_p2p=check.is_p2p,
            created_at=check.created_at
        )

        return CheckUpdateResponse(
            success=True,
            message="Transaction updated successfully",
            check=response_check
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
    finally:
        db.close()


@router.delete("/{transaction_id}", response_model=DeleteResponse)
async def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db_session)
):
    """
    Delete a check (transaction) by ID

    - **transaction_id**: ID of check to delete

    Permanently removes the record from database.
    """
    try:
        check = db.query(Check).filter(Check.id == transaction_id).first()

        if not check:
            raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")

        db.delete(check)
        db.commit()

        return DeleteResponse(
            success=True,
            message="Transaction deleted successfully",
            deleted_id=transaction_id
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
    finally:
        db.close()


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_transactions(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db_session)
):
    """
    Delete multiple checks (transactions) at once

    - **ids**: List of check IDs to delete (max 100 per request)

    Returns count of deleted records and any errors.
    """
    try:
        deleted_count = 0
        failed_ids = []
        errors = []

        for transaction_id in request.ids:
            try:
                check = db.query(Check).filter(Check.id == transaction_id).first()
                if check:
                    db.delete(check)
                    deleted_count += 1
                else:
                    failed_ids.append(transaction_id)
                    errors.append(f"ID {transaction_id} not found")
            except Exception as e:
                failed_ids.append(transaction_id)
                errors.append(f"ID {transaction_id}: {str(e)}")

        db.commit()

        return BulkDeleteResponse(
            success=len(failed_ids) == 0,
            deleted_count=deleted_count,
            failed_ids=failed_ids,
            errors=errors
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Bulk delete failed: {str(e)}")
    finally:
        db.close()
