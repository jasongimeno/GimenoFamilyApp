from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.db.database import get_db
from app.models.user import User
from app.models.carpool import CarpoolEvent
from app.schemas.carpool import CarpoolEventCreate, CarpoolEventResponse, CarpoolEventUpdate, CarpoolSearchQuery
from app.utils.auth import get_current_user
from app.core.config import ENABLE_SEARCH

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
    
    # Update in search service - but don't block if it fails
    try:
        if ENABLE_SEARCH:
            from app.utils.azure_search import index_carpool_event as azure_index_carpool_event
            index_success = azure_index_carpool_event(event)
            if not index_success:
                logger.warning(f"Failed to index carpool event ID {event.id} in Azure Search, but event was updated in database")
    except Exception as e:
        # If indexing fails, just log the error
        logger.warning(f"Error occurred during carpool event indexing on update: {str(e)}")
    
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
    
    # Delete from search service - but don't block if it fails
    try:
        if ENABLE_SEARCH:
            from app.utils.azure_search import delete_document, CARPOOL_INDEX
            delete_document(CARPOOL_INDEX, event_id)
    except Exception as e:
        # If deletion from search service fails, just log the error
        logger.warning(f"Error occurred during carpool event deletion from search service: {str(e)}")
    
    return None

# Search carpool events
@router.post("/search", response_model=List[CarpoolEventResponse])
def search_events(
    search_query: CarpoolSearchQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    search_results = {"hits": {"hits": []}}
    
    # Use Azure Cognitive Search if enabled
    if ENABLE_SEARCH:
        try:
            from app.utils.azure_search import search_carpool_events as azure_search_carpool_events
            from app.utils.azure_search import search_available
            
            # Log the search availability status
            logger.info(f"Azure Search available: {search_available}")
            
            # Perform the search
            search_results = azure_search_carpool_events(current_user.id, search_query.query)
            logger.info(f"Using Azure Cognitive Search for carpool search with query: {search_query.query}")
            
            # Log the search results structure
            logger.debug(f"Search results: {search_results}")
        except ImportError as e:
            logger.warning(f"Azure Cognitive Search module not found: {str(e)}")
        except Exception as e:
            logger.error(f"Error using Azure Cognitive Search: {str(e)}", exc_info=True)
    else:
        logger.info("Search is disabled in configuration")
    
    # Extract event IDs
    event_ids = [hit["_source"]["id"] for hit in search_results["hits"]["hits"]]
    logger.info(f"Found {len(event_ids)} event IDs from search")
    
    # Get events from database
    events = []
    if event_ids:
        for event_id in event_ids:
            event = db.query(CarpoolEvent).filter(CarpoolEvent.id == event_id).first()
            if event:
                events.append(event)
    else:
        # Fallback to database search if Azure Search returns no results
        logger.info(f"Azure Search returned no results, falling back to database search for query: {search_query.query}")
        events = search_carpool_events_in_database(db, current_user.id, search_query.query)
    
    return events

# Helper function for database fallback search
def search_carpool_events_in_database(db: Session, user_id: int, query: str, limit: int = 100):
    """
    Search for carpool events in the database using a flexible search approach.
    This is used as a fallback when Azure Search is unavailable or returns no results.
    """
    if not query or query.strip() == "*" or query.strip() == "":
        # If no specific search query, return recent events
        logger.info("No specific search query provided, returning recent carpool events")
        return db.query(CarpoolEvent).filter(
            CarpoolEvent.user_id == user_id
        ).order_by(CarpoolEvent.created_at.desc()).limit(limit).all()
    
    # Split the query into words for flexible searching
    search_terms = query.strip().lower().split()
    logger.info(f"Searching database for carpool events with terms: {search_terms}")
    
    # Build a query that searches in description, destination, and notes
    from sqlalchemy import or_
    
    # Start with a base query for the user's events
    base_query = db.query(CarpoolEvent).filter(CarpoolEvent.user_id == user_id)
    
    # For each search term, add OR conditions for description, destination, and notes
    for term in search_terms:
        like_term = f"%{term}%"
        base_query = base_query.filter(
            or_(
                CarpoolEvent.description.ilike(like_term),
                CarpoolEvent.destination.ilike(like_term),
                CarpoolEvent.notes.ilike(like_term)
            )
        )
    
    # Order by creation date and limit results
    results = base_query.order_by(CarpoolEvent.created_at.desc()).limit(limit).all()
    logger.info(f"Database search returned {len(results)} carpool events")
    
    return results 