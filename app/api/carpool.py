from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.db.database import get_db
from app.models.user import User
from app.models.carpool import CarpoolEvent
from app.schemas.carpool import CarpoolEventCreate, CarpoolEventResponse, CarpoolEventUpdate, CarpoolSearchQuery
from app.utils.auth import get_current_user
from app.utils.elastic import delete_document, CARPOOL_INDEX
from app.core.config import ENABLE_ELASTICSEARCH, ENABLE_SEARCH

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/carpool", tags=["Carpool Management"])

# Create a new carpool event
@router.post("/events", response_model=CarpoolEventResponse, status_code=status.HTTP_201_CREATED)
def create_carpool_event(
    event_data: CarpoolEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Create carpool event
    db_event = CarpoolEvent(
        user_id=current_user.id,
        description=event_data.description,
        destination=event_data.destination,
        drop_off_time=event_data.drop_off_time,
        notes=event_data.notes
    )
    
    # Add to database
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    # Index in search service - but don't block if it fails
    try:
        if ENABLE_SEARCH:
            from app.utils.azure_search import index_carpool_event as azure_index_carpool_event
            index_success = azure_index_carpool_event(db_event)
            if not index_success:
                logger.warning(f"Failed to index carpool event ID {db_event.id} in Azure Search, but event was created in database")
        elif ENABLE_ELASTICSEARCH:
            from app.utils.elastic import index_carpool_event as es_index_carpool_event
            index_success = es_index_carpool_event(db_event)
            if not index_success:
                logger.warning(f"Failed to index carpool event ID {db_event.id} in Elasticsearch, but event was created in database")
    except Exception as e:
        # If indexing fails, just log the error
        logger.warning(f"Error occurred during carpool event indexing: {str(e)}")
    
    return db_event

# Get all carpool events for the current user
@router.get("/events", response_model=List[CarpoolEventResponse])
def get_carpool_events(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get events for the current user ordered by drop_off_time
    events = db.query(CarpoolEvent).filter(
        CarpoolEvent.user_id == current_user.id
    ).order_by(CarpoolEvent.drop_off_time).offset(skip).limit(limit).all()
    
    return events

# Get a specific carpool event
@router.get("/events/{event_id}", response_model=CarpoolEventResponse)
def get_carpool_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get event
    event = db.query(CarpoolEvent).filter(
        CarpoolEvent.id == event_id,
        CarpoolEvent.user_id == current_user.id
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpool event not found"
        )
    
    return event

# Update a carpool event
@router.put("/events/{event_id}", response_model=CarpoolEventResponse)
def update_carpool_event(
    event_id: int,
    event_data: CarpoolEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get event
    event = db.query(CarpoolEvent).filter(
        CarpoolEvent.id == event_id,
        CarpoolEvent.user_id == current_user.id
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpool event not found"
        )
    
    # Update event
    event.description = event_data.description
    event.destination = event_data.destination
    event.drop_off_time = event_data.drop_off_time
    event.notes = event_data.notes
    
    db.commit()
    db.refresh(event)
    
    # Update in Elasticsearch - but don't block if it fails
    try:
        index_success = index_carpool_event(event)
        if not index_success:
            # Log the failure, but don't halt the process
            print(f"Warning: Failed to index carpool event ID {event.id} in Elasticsearch during update, but event was updated in database")
    except Exception as e:
        # If indexing fails, just log the error
        print(f"Warning: Error occurred during carpool event indexing on update: {str(e)}")
    
    return event

# Delete a carpool event
@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_carpool_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get event
    event = db.query(CarpoolEvent).filter(
        CarpoolEvent.id == event_id,
        CarpoolEvent.user_id == current_user.id
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpool event not found"
        )
    
    # Delete from database
    db.delete(event)
    db.commit()
    
    # Delete from Elasticsearch - but don't block if it fails
    try:
        delete_document(CARPOOL_INDEX, event_id)
    except Exception as e:
        # If deletion from Elasticsearch fails, just log the error
        print(f"Warning: Error occurred during carpool event deletion from Elasticsearch: {str(e)}")
    
    return None

# Search carpool events
@router.post("/search", response_model=List[CarpoolEventResponse])
def search_events(
    search_query: CarpoolSearchQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    search_results = {"hits": {"hits": []}}
    
    # Try Azure Cognitive Search first if enabled
    if ENABLE_SEARCH:
        try:
            from app.utils.azure_search import search_carpool_events as azure_search_carpool_events
            search_results = azure_search_carpool_events(current_user.id, search_query.query)
            logger.info(f"Using Azure Cognitive Search for carpool search with query: {search_query.query}")
        except ImportError:
            logger.warning("Azure Cognitive Search module not found, falling back to Elasticsearch")
        except Exception as e:
            logger.error(f"Error using Azure Cognitive Search: {str(e)}, falling back to Elasticsearch")
    
    # Fallback to Elasticsearch if Azure Search failed or is disabled
    if not search_results["hits"]["hits"] and ENABLE_ELASTICSEARCH:
        try:
            from app.utils.elastic import search_carpool_events as es_search_carpool_events
            search_results = es_search_carpool_events(current_user.id, search_query.query)
            logger.info(f"Using Elasticsearch for carpool search with query: {search_query.query}")
        except ImportError:
            logger.warning("Elasticsearch module not found")
        except Exception as e:
            logger.error(f"Error using Elasticsearch: {str(e)}")
    
    # Extract event IDs
    event_ids = [hit["_source"]["id"] for hit in search_results["hits"]["hits"]]
    
    # Get events from database
    events = []
    for event_id in event_ids:
        event = db.query(CarpoolEvent).filter(CarpoolEvent.id == event_id).first()
        if event:
            events.append(event)
    
    return events 