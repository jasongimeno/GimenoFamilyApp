from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from app.db.database import get_db
from app.models.user import User
from app.models.checklist import Checklist, ChecklistItem, ChecklistRun, ChecklistRunItem
from app.schemas.checklist import (
    ChecklistCreate, ChecklistResponse, ChecklistUpdate, 
    ChecklistRunCreate, ChecklistRunResponse, ChecklistRunItemUpdate,
    CompleteChecklistRunRequest
)
from app.utils.auth import get_current_user
from app.utils.email import send_checklist_report, generate_checklist_report_html
from app.core.config import ENABLE_SEARCH

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/checklists", tags=["Checklists"])

# Create a new checklist
@router.post("/", response_model=ChecklistResponse, status_code=status.HTTP_201_CREATED)
def create_checklist(
    checklist_data: ChecklistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Create checklist
    db_checklist = Checklist(
        user_id=current_user.id,
        title=checklist_data.title,
        category=checklist_data.category
    )
    
    # Add to database
    db.add(db_checklist)
    db.commit()
    db.refresh(db_checklist)
    
    # Create checklist items
    db_items = []
    for item_data in checklist_data.items:
        db_item = ChecklistItem(
            checklist_id=db_checklist.id,
            text=item_data.text,
            is_required=item_data.is_required
        )
        db.add(db_item)
        db_items.append(db_item)
    
    db.commit()
    
    # Refresh items to get their ids
    for item in db_items:
        db.refresh(item)
    
    # Index in search service - but don't block if it fails
    try:
        if ENABLE_SEARCH:
            from app.utils.azure_search import index_checklist
            index_success = index_checklist(db_checklist, db_items)
            if not index_success:
                # Log the failure, but don't halt the process
                logger.warning(f"Failed to index checklist ID {db_checklist.id} in Azure Search, but checklist was created in database")
    except Exception as e:
        # If indexing fails, just log the error
        logger.warning(f"Error occurred during checklist indexing: {str(e)}")
    
    # Prepare response
    response = ChecklistResponse(
        id=db_checklist.id,
        user_id=db_checklist.user_id,
        title=db_checklist.title,
        category=db_checklist.category,
        created_at=db_checklist.created_at,
        items=[{
            "id": item.id,
            "checklist_id": item.checklist_id,
            "text": item.text,
            "is_required": item.is_required
        } for item in db_items]
    )
    
    return response

# Get all checklists for the current user
@router.get("/", response_model=List[ChecklistResponse])
def get_checklists(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get checklists for the current user
    checklists = db.query(Checklist).filter(Checklist.user_id == current_user.id).offset(skip).limit(limit).all()
    
    # Prepare response with items
    result = []
    for checklist in checklists:
        items = db.query(ChecklistItem).filter(ChecklistItem.checklist_id == checklist.id).all()
        result.append(
            ChecklistResponse(
                id=checklist.id,
                user_id=checklist.user_id,
                title=checklist.title,
                category=checklist.category,
                created_at=checklist.created_at,
                items=[{
                    "id": item.id,
                    "checklist_id": item.checklist_id,
                    "text": item.text,
                    "is_required": item.is_required
                } for item in items]
            )
        )
    
    return result

# Get a specific checklist by ID
@router.get("/{checklist_id}", response_model=ChecklistResponse)
def get_checklist(
    checklist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get checklist
    checklist = db.query(Checklist).filter(Checklist.id == checklist_id, Checklist.user_id == current_user.id).first()
    if not checklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checklist not found"
        )
    
    # Get items
    items = db.query(ChecklistItem).filter(ChecklistItem.checklist_id == checklist.id).all()
    
    # Prepare response
    response = ChecklistResponse(
        id=checklist.id,
        user_id=checklist.user_id,
        title=checklist.title,
        category=checklist.category,
        created_at=checklist.created_at,
        items=[{
            "id": item.id,
            "checklist_id": item.checklist_id,
            "text": item.text,
            "is_required": item.is_required
        } for item in items]
    )
    
    return response

# Update a checklist
@router.put("/{checklist_id}", response_model=ChecklistResponse)
def update_checklist(
    checklist_id: int,
    checklist_data: ChecklistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get checklist
    checklist = db.query(Checklist).filter(Checklist.id == checklist_id, Checklist.user_id == current_user.id).first()
    if not checklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checklist not found"
        )
    
    # Update checklist properties
    checklist.title = checklist_data.title
    checklist.category = checklist_data.category
    
    # Get existing items
    existing_items = db.query(ChecklistItem).filter(ChecklistItem.checklist_id == checklist.id).all()
    existing_item_map = {item.id: item for item in existing_items}
    
    # Track which items to keep
    items_to_keep_ids = set()
    db_items = []
    
    # Create new items or update existing ones
    for i, item_data in enumerate(checklist_data.items):
        # If this is an existing item that was just edited and still in the same position
        if i < len(existing_items):
            existing_item = existing_items[i]
            existing_item.text = item_data.text
            existing_item.is_required = item_data.is_required
            db_items.append(existing_item)
            items_to_keep_ids.add(existing_item.id)
            print(f"Updated existing item {existing_item.id}: {item_data.text}")
        else:
            # This is a new item
            db_item = ChecklistItem(
                checklist_id=checklist.id,
                text=item_data.text,
                is_required=item_data.is_required
            )
            db.add(db_item)
            db_items.append(db_item)
            print(f"Added new item: {item_data.text}")
    
    # Delete items that no longer exist
    items_deleted = 0
    for item_id, item in existing_item_map.items():
        if item_id not in items_to_keep_ids:
            db.delete(item)
            items_deleted += 1
    
    print(f"Deleted {items_deleted} items that were removed")
    
    db.commit()
    
    # Refresh everything
    db.refresh(checklist)
    for item in db_items:
        db.refresh(item)
    
    print(f"Update complete, checklist now has {len(db_items)} items")
    
    # Update in search service - but don't block if it fails
    try:
        if ENABLE_SEARCH:
            from app.utils.azure_search import index_checklist
            index_success = index_checklist(checklist, db_items)
            if not index_success:
                # Log the failure, but don't halt the process
                logger.warning(f"Failed to index checklist ID {checklist.id} in Azure Search during update, but checklist was updated in database")
    except Exception as e:
        # If indexing fails, just log the error
        logger.warning(f"Error occurred during checklist indexing on update: {str(e)}")
    
    # Prepare response
    response = ChecklistResponse(
        id=checklist.id,
        user_id=checklist.user_id,
        title=checklist.title,
        category=checklist.category,
        created_at=checklist.created_at,
        items=[{
            "id": item.id,
            "checklist_id": item.checklist_id,
            "text": item.text,
            "is_required": item.is_required
        } for item in db_items]
    )
    
    return response

# Delete a checklist
@router.delete("/{checklist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_checklist(
    checklist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get checklist
    checklist = db.query(Checklist).filter(Checklist.id == checklist_id, Checklist.user_id == current_user.id).first()
    if not checklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checklist not found"
        )
    
    # Delete from database (cascade will delete items and runs)
    db.delete(checklist)
    db.commit()
    
    # Delete from search service - but don't block if it fails
    try:
        if ENABLE_SEARCH:
            from app.utils.azure_search import delete_document, CHECKLIST_INDEX
            delete_document(CHECKLIST_INDEX, checklist_id)
    except Exception as e:
        # If deletion from search service fails, just log the error
        logger.warning(f"Error occurred during checklist deletion from search service: {str(e)}")
    
    return None

# Start a new checklist run
@router.post("/runs", response_model=ChecklistRunResponse, status_code=status.HTTP_201_CREATED)
def start_checklist_run(
    run_data: ChecklistRunCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify checklist exists and belongs to user
    checklist = db.query(Checklist).filter(Checklist.id == run_data.checklist_id, Checklist.user_id == current_user.id).first()
    if not checklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checklist not found"
        )
    
    # Create run
    db_run = ChecklistRun(
        checklist_id=run_data.checklist_id,
        email_sent_to=run_data.email_sent_to,
        notes=run_data.notes
    )
    
    # Add to database
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    
    # Get checklist items
    checklist_items = db.query(ChecklistItem).filter(ChecklistItem.checklist_id == checklist.id).all()
    
    # Create run items
    run_items = []
    for item in checklist_items:
        db_run_item = ChecklistRunItem(
            run_id=db_run.id,
            item_id=item.id,
            completed=False,
            notes=None
        )
        db.add(db_run_item)
        run_items.append(db_run_item)
    
    db.commit()
    
    # Refresh run items to get their ids
    for run_item in run_items:
        db.refresh(run_item)
    
    # Prepare response
    response = ChecklistRunResponse(
        id=db_run.id,
        checklist_id=db_run.checklist_id,
        started_at=db_run.started_at,
        completed_at=db_run.completed_at,
        email_sent_to=db_run.email_sent_to,
        notes=db_run.notes,
        run_items=[{
            "id": run_item.id,
            "run_id": run_item.run_id,
            "item_id": run_item.item_id,
            "completed": run_item.completed,
            "notes": run_item.notes
        } for run_item in run_items]
    )
    
    return response

# Get a checklist run
@router.get("/runs/{run_id}", response_model=ChecklistRunResponse)
def get_checklist_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get run and verify ownership
    run = db.query(ChecklistRun).join(Checklist).filter(
        ChecklistRun.id == run_id,
        Checklist.user_id == current_user.id
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checklist run not found"
        )
    
    # Get run items
    run_items = db.query(ChecklistRunItem).filter(ChecklistRunItem.run_id == run.id).all()
    
    # Prepare response
    response = ChecklistRunResponse(
        id=run.id,
        checklist_id=run.checklist_id,
        started_at=run.started_at,
        completed_at=run.completed_at,
        email_sent_to=run.email_sent_to,
        notes=run.notes,
        run_items=[{
            "id": run_item.id,
            "run_id": run_item.run_id,
            "item_id": run_item.item_id,
            "completed": run_item.completed,
            "notes": run_item.notes
        } for run_item in run_items]
    )
    
    return response

# Update a run item status
@router.put("/runs/{run_id}/items/{item_id}", status_code=status.HTTP_200_OK)
def update_run_item(
    run_id: int,
    item_id: int,
    item_data: ChecklistRunItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify run exists and belongs to user
    run = db.query(ChecklistRun).join(Checklist).filter(
        ChecklistRun.id == run_id,
        Checklist.user_id == current_user.id
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checklist run not found"
        )
    
    # Get run item
    run_item = db.query(ChecklistRunItem).filter(
        ChecklistRunItem.run_id == run_id,
        ChecklistRunItem.item_id == item_id
    ).first()
    
    if not run_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run item not found"
        )
    
    # Update run item
    run_item.completed = item_data.completed
    run_item.notes = item_data.notes
    
    db.commit()
    db.refresh(run_item)
    
    return {"success": True}

# Get all runs for a specific checklist
@router.get("/{checklist_id}/runs", response_model=List[ChecklistRunResponse])
def get_checklist_runs(
    checklist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify checklist exists and belongs to user
    checklist = db.query(Checklist).filter(Checklist.id == checklist_id, Checklist.user_id == current_user.id).first()
    if not checklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checklist not found"
        )
    
    # Get all runs for this checklist
    runs = db.query(ChecklistRun).filter(ChecklistRun.checklist_id == checklist_id).order_by(ChecklistRun.started_at.desc()).all()
    
    # Prepare response
    response = []
    for run in runs:
        # Get run items
        run_items = db.query(ChecklistRunItem).filter(ChecklistRunItem.run_id == run.id).all()
        
        # Add to response
        response.append(ChecklistRunResponse(
            id=run.id,
            checklist_id=run.checklist_id,
            started_at=run.started_at,
            completed_at=run.completed_at,
            email_sent_to=run.email_sent_to,
            notes=run.notes,
            run_items=[{
                "id": run_item.id,
                "run_id": run_item.run_id,
                "item_id": run_item.item_id,
                "completed": run_item.completed,
                "notes": run_item.notes
            } for run_item in run_items]
        ))
    
    return response

# Complete a checklist run
@router.post("/runs/{run_id}/complete", response_model=ChecklistRunResponse)
def complete_checklist_run(
    run_id: int,
    complete_data: CompleteChecklistRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify run exists and belongs to user
    run = db.query(ChecklistRun).join(Checklist).filter(
        ChecklistRun.id == run_id,
        Checklist.user_id == current_user.id
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checklist run not found"
        )
    
    # Check if run is already completed
    if run.completed_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Checklist run already completed"
        )
    
    # Get checklist
    checklist = db.query(Checklist).filter(Checklist.id == run.checklist_id).first()
    
    # Get run items with associated checklist items
    run_items = db.query(ChecklistRunItem).filter(ChecklistRunItem.run_id == run.id).all()
    
    # Check if required items are completed
    required_items = db.query(ChecklistItem).filter(
        ChecklistItem.checklist_id == run.checklist_id,
        ChecklistItem.is_required == True
    ).all()
    
    required_item_ids = {item.id for item in required_items}
    completed_required_item_ids = {
        item.item_id for item in run_items 
        if item.completed and item.item_id in required_item_ids
    }
    
    if len(completed_required_item_ids) < len(required_item_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not all required items are completed"
        )
    
    # Update run
    run.completed_at = datetime.now()
    
    if complete_data.email_sent_to:
        run.email_sent_to = complete_data.email_sent_to
    
    if complete_data.notes:
        run.notes = complete_data.notes
    
    db.commit()
    db.refresh(run)
    
    # Generate and send report if email is provided
    if run.email_sent_to:
        # Get items with their texts
        items_with_text = []
        for run_item in run_items:
            item = db.query(ChecklistItem).filter(ChecklistItem.id == run_item.item_id).first()
            if item:
                run_item.item = item
                items_with_text.append(run_item)
        
        # Generate HTML report
        html_content = generate_checklist_report_html(checklist, run, items_with_text)
        
        # Send email
        subject = f"Checklist Completed: {checklist.title}"
        send_checklist_report(run.email_sent_to, subject, html_content)
    
    # Prepare response
    response = ChecklistRunResponse(
        id=run.id,
        checklist_id=run.checklist_id,
        started_at=run.started_at,
        completed_at=run.completed_at,
        email_sent_to=run.email_sent_to,
        notes=run.notes,
        run_items=[{
            "id": run_item.id,
            "run_id": run_item.run_id,
            "item_id": run_item.item_id,
            "completed": run_item.completed,
            "notes": run_item.notes
        } for run_item in run_items]
    )
    
    return response

# Search checklists
@router.get("/search", response_model=List[ChecklistResponse])
def search(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    search_results = {"hits": {"hits": []}}
    
    # Use Azure Cognitive Search if enabled
    if ENABLE_SEARCH:
        try:
            from app.utils.azure_search import search_checklists
            from app.utils.azure_search import search_available
            
            # Check and log if search is available
            logger.info(f"Azure Search available: {search_available}")
            
            # Log the search query
            logger.info(f"Searching checklists with query: '{q}' for user: {current_user.id}")
            
            search_results = search_checklists(current_user.id, q)
            logger.info(f"Using Azure Cognitive Search for checklist search with query: {q}")
            
            # Log search results for debugging
            logger.info(f"Search results: {search_results}")
            
            # If no results, try a fallback database search
            if not search_results["hits"]["hits"]:
                logger.warning(f"No results from Azure Search, trying database fallback")
                return search_checklists_in_database(db, current_user.id, q)
        except ImportError as e:
            logger.warning(f"Azure Cognitive Search module not found: {str(e)}")
            return search_checklists_in_database(db, current_user.id, q)
        except Exception as e:
            logger.error(f"Error using Azure Cognitive Search: {str(e)}", exc_info=True)
            return search_checklists_in_database(db, current_user.id, q)
    else:
        # If search is disabled, use database search
        logger.info("Search is disabled, using database search")
        return search_checklists_in_database(db, current_user.id, q)
    
    # Extract checklist IDs
    checklist_ids = [hit["_source"]["id"] for hit in search_results["hits"]["hits"]]
    logger.info(f"Found {len(checklist_ids)} checklist IDs from search")
    
    # Get checklists from database
    result = []
    for checklist_id in checklist_ids:
        checklist = db.query(Checklist).filter(Checklist.id == checklist_id).first()
        if checklist:
            items = db.query(ChecklistItem).filter(ChecklistItem.checklist_id == checklist.id).all()
            result.append(ChecklistResponse(
                id=checklist.id,
                user_id=checklist.user_id,
                title=checklist.title,
                category=checklist.category,
                created_at=checklist.created_at,
                items=[{
                    "id": item.id,
                    "checklist_id": item.checklist_id,
                    "text": item.text,
                    "is_required": item.is_required
                } for item in items]
            ))
    
    logger.info(f"Returning {len(result)} checklists from search")
    return result

def search_checklists_in_database(db, user_id, query, limit=10):
    """Search checklists in the database as a fallback when Azure Search is unavailable"""
    logger.info(f"Performing database search for: '{query}'")
    
    # Use a more flexible search by splitting the query into words
    search_terms = query.lower().split()
    
    if not search_terms:
        # If no search terms, return recent checklists
        checklists = db.query(Checklist).filter(
            Checklist.user_id == user_id
        ).order_by(Checklist.created_at.desc()).limit(limit).all()
        
        logger.info(f"Empty search term, returning {len(checklists)} recent checklists")
        
        # Get items for each checklist
        result = []
        for checklist in checklists:
            items = db.query(ChecklistItem).filter(ChecklistItem.checklist_id == checklist.id).all()
            result.append(ChecklistResponse(
                id=checklist.id,
                user_id=checklist.user_id,
                title=checklist.title,
                category=checklist.category,
                created_at=checklist.created_at,
                items=[{
                    "id": item.id,
                    "checklist_id": item.checklist_id,
                    "text": item.text,
                    "is_required": item.is_required
                } for item in items]
            ))
        
        return result
    
    # Build a query that searches for any of the terms in title and category
    from sqlalchemy import or_
    conditions = []
    
    for term in search_terms:
        conditions.append(Checklist.title.ilike(f"%{term}%"))
        conditions.append(Checklist.category.ilike(f"%{term}%"))
    
    # We also need to search in checklist items, which requires a join
    # First, find checklists matching the search terms
    matching_checklists = db.query(Checklist).filter(
        Checklist.user_id == user_id,
        or_(*conditions)
    ).all()
    
    # Then, find checklists with items matching the search terms
    item_conditions = []
    for term in search_terms:
        item_conditions.append(ChecklistItem.text.ilike(f"%{term}%"))
    
    checklists_with_matching_items = db.query(Checklist).join(
        ChecklistItem, Checklist.id == ChecklistItem.checklist_id
    ).filter(
        Checklist.user_id == user_id,
        or_(*item_conditions)
    ).all()
    
    # Combine the results (removing duplicates)
    all_checklists = {}
    for checklist in matching_checklists + checklists_with_matching_items:
        all_checklists[checklist.id] = checklist
    
    # Now get all the matching checklists with their items
    result = []
    for checklist in all_checklists.values():
        items = db.query(ChecklistItem).filter(ChecklistItem.checklist_id == checklist.id).all()
        result.append(ChecklistResponse(
            id=checklist.id,
            user_id=checklist.user_id,
            title=checklist.title,
            category=checklist.category,
            created_at=checklist.created_at,
            items=[{
                "id": item.id,
                "checklist_id": item.checklist_id,
                "text": item.text,
                "is_required": item.is_required
            } for item in items]
        ))
    
    # Sort by created_at (newest first) and limit
    result.sort(key=lambda x: x.created_at, reverse=True)
    if limit and len(result) > limit:
        result = result[:limit]
    
    logger.info(f"Database search found {len(result)} checklists")
    return result
 