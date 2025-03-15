from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
import logging

from app.db.database import get_db
from app.models.user import User
from app.models.checklist import Checklist, ChecklistItem, ChecklistRun, ChecklistRunItem
from app.schemas.checklist import (
    ChecklistCreate, ChecklistResponse, ChecklistUpdate, 
    ChecklistRunCreate, ChecklistRunResponse, ChecklistRunItemUpdate,
    ChecklistReportRequest
)
from app.utils.auth import get_current_user
from app.utils.elastic import index_checklist, delete_document, CHECKLIST_INDEX
from app.utils.email import send_checklist_report, generate_checklist_report_html
from app.core.config import ENABLE_ELASTICSEARCH, ENABLE_SEARCH
from app.utils.azure_search import search_checklists as azure_search_checklists
from app.utils.logger import logger

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
    
    # Index in Elasticsearch - but don't block if it fails
    try:
        index_success = index_checklist(db_checklist, db_items)
        if not index_success:
            # Log the failure, but don't halt the process
            print(f"Warning: Failed to index checklist ID {db_checklist.id} in Elasticsearch, but checklist was created in database")
    except Exception as e:
        # If indexing fails, just log the error
        print(f"Warning: Error occurred during checklist indexing: {str(e)}")
    
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
    
    # Log the update request
    print(f"Updating checklist {checklist_id} with {len(checklist_data.items)} items")
    print(f"Request data: Title = '{checklist_data.title}', Category = '{checklist_data.category}'")
    for i, item in enumerate(checklist_data.items):
        print(f"  Item {i+1}: '{item.text}' (Required: {item.is_required})")
    
    # Update checklist
    checklist.title = checklist_data.title
    checklist.category = checklist_data.category
    
    # Get existing items
    existing_items = db.query(ChecklistItem).filter(ChecklistItem.checklist_id == checklist.id).all()
    existing_item_map = {item.id: item for item in existing_items}
    
    print(f"Checklist has {len(existing_items)} existing items")
    
    # Process items - we'll track which existing items to keep
    db_items = []
    items_to_keep_ids = set()
    
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
    
    # Update in Elasticsearch - but don't block if it fails
    try:
        index_success = index_checklist(checklist, db_items)
        if not index_success:
            # Log the failure, but don't halt the process
            print(f"Warning: Failed to index checklist ID {checklist.id} in Elasticsearch during update, but checklist was updated in database")
    except Exception as e:
        # If indexing fails, just log the error
        print(f"Warning: Error occurred during checklist indexing on update: {str(e)}")
    
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
    
    # Delete from Elasticsearch
    delete_document(CHECKLIST_INDEX, checklist_id)
    
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
    complete_data: ChecklistReportRequest,
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
    
    # Try Azure Cognitive Search first if enabled
    if ENABLE_SEARCH:
        try:
            from app.utils.azure_search import search_checklists as azure_search_checklists
            search_results = azure_search_checklists(current_user.id, q)
            logger.info(f"Using Azure Cognitive Search for checklist search with query: {q}")
        except ImportError:
            logger.warning("Azure Cognitive Search module not found, falling back to Elasticsearch")
        except Exception as e:
            logger.error(f"Error using Azure Cognitive Search: {str(e)}, falling back to Elasticsearch")
    
    # Fallback to Elasticsearch if Azure Search failed or is disabled
    if not search_results["hits"]["hits"] and ENABLE_ELASTICSEARCH:
        try:
            from app.utils.elastic import search_checklists as es_search_checklists
            search_results = es_search_checklists(current_user.id, q)
            logger.info(f"Using Elasticsearch for checklist search with query: {q}")
        except ImportError:
            logger.warning("Elasticsearch module not found")
        except Exception as e:
            logger.error(f"Error using Elasticsearch: {str(e)}")
    
    # Extract checklist IDs
    checklist_ids = [hit["_source"]["id"] for hit in search_results["hits"]["hits"]]
    
    # Get checklists from database
    result = []
    for checklist_id in checklist_ids:
        checklist = db.query(Checklist).filter(Checklist.id == checklist_id).first()
        if checklist:
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
 