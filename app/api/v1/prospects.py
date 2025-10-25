"""
Prospects API endpoints
Handles lead/customer management with event publishing
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from datetime import date

from app.api.dependencies import get_db_session
from app.models.prospect import Prospect, ProspectType, ProspectStatus, RiskCategory
from app.events.prospect_events import ProspectCreated
from app.events.publisher import EventPublisher

router = APIRouter()


# Pydantic schemas for request/response
class ProspectCreate(BaseModel):
    """Schema for creating a new prospect"""
    type: ProspectType
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    birth_date: date | None = None
    tax_code: str | None = Field(None, max_length=20)
    notes: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "type": "individual",
                "first_name": "Marco",
                "last_name": "Rossi",
                "email": "marco.rossi@example.com",
                "phone": "+39 333 1234567",
                "birth_date": "1985-03-15",
                "tax_code": "RSSMRC85C15H501Z",
                "notes": "Interested in life insurance"
            }
        }


class ProspectResponse(BaseModel):
    """Schema for prospect response"""
    id: int
    type: ProspectType
    first_name: str
    last_name: str
    email: str
    phone: str
    birth_date: date | None
    tax_code: str | None
    status: ProspectStatus
    risk_category: RiskCategory | None
    assigned_broker: int | None
    created_by: int
    notes: str | None

    class Config:
        from_attributes = True


@router.post("/", response_model=ProspectResponse, status_code=status.HTTP_201_CREATED)
async def create_prospect(
    prospect_data: ProspectCreate,
    db: Session = Depends(get_db_session)
):
    """
    Create a new prospect and publish ProspectCreated event.

    This is the **top-down entry point** for the event-driven flow:
    1. Create prospect in database
    2. Publish ProspectCreated event to Redis
    3. ARQ workers consume event
    4. Event handlers react (send emails, log audit, etc.)

    The API responds immediately - handlers run asynchronously.
    """
    # TODO: Get current user from auth
    # For now, hardcode user_id = 1 (admin)
    current_user_id = 1

    # Create prospect in database
    prospect = Prospect(
        type=prospect_data.type,
        first_name=prospect_data.first_name,
        last_name=prospect_data.last_name,
        email=prospect_data.email,
        phone=prospect_data.phone,
        birth_date=prospect_data.birth_date,
        tax_code=prospect_data.tax_code,
        status=ProspectStatus.NEW,
        created_by=current_user_id,
        notes=prospect_data.notes,
    )

    db.add(prospect)
    db.commit()
    db.refresh(prospect)

    # Publish ProspectCreated event
    event = ProspectCreated(
        prospect_id=prospect.id,
        prospect_type=prospect.type.value,
        email=prospect.email,
        full_name=prospect.full_name,
        created_by_user_id=current_user_id,
    )

    try:
        await EventPublisher.publish(event, db=db)
    except Exception as e:
        # Log error but don't fail the request
        # Event publishing failure shouldn't block prospect creation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to publish ProspectCreated event: {e}")

    return prospect


@router.get("/", response_model=List[ProspectResponse])
def list_prospects(
    skip: int = 0,
    limit: int = 100,
    status: ProspectStatus | None = None,
    db: Session = Depends(get_db_session)
):
    """
    List all prospects with optional filtering.

    Query parameters:
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    - status: Filter by prospect status (new, contacted, quoted, etc.)
    """
    query = db.query(Prospect)

    if status:
        query = query.filter(Prospect.status == status)

    prospects = query.offset(skip).limit(limit).all()
    return prospects


@router.get("/{prospect_id}", response_model=ProspectResponse)
def get_prospect(
    prospect_id: int,
    db: Session = Depends(get_db_session)
):
    """
    Get a single prospect by ID.

    Returns 404 if prospect not found.
    """
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id).first()

    if not prospect:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prospect with id {prospect_id} not found"
        )

    return prospect


@router.delete("/{prospect_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prospect(
    prospect_id: int,
    db: Session = Depends(get_db_session)
):
    """
    Delete a prospect by ID.

    Returns 404 if prospect not found.
    """
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id).first()

    if not prospect:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prospect with id {prospect_id} not found"
        )

    db.delete(prospect)
    db.commit()

    return None
