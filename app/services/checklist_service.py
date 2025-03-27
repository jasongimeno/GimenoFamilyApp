from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict
import logging
from datetime import datetime

# Import your models - the exact import paths may need adjustment
from app.models.checklist import Checklist, ChecklistItem

logger = logging.getLogger(__name__)

class ChecklistService:
    def __init__(self, db: Session):
        self.db = db
    
    def add_items_to_weekly_checklist(
        self, 
        user_id: int, 
        checklist_name: str, 
        items: List[str]
    ) -> Dict:
        """
        Add items to weekly shopping list.
        Creates the list if it doesn't exist.
        """
        # Check if the checklist already exists
        checklist = self.db.query(Checklist).filter(
            and_(
                Checklist.user_id == user_id,
                Checklist.title == checklist_name
            )
        ).first()
        
        # Create the checklist if it doesn't exist
        if not checklist:
            checklist = Checklist(
                title=checklist_name,
                user_id=user_id,
                category="Shopping"
            )
            self.db.add(checklist)
            self.db.commit()
            self.db.refresh(checklist)
            logger.info(f"Created new checklist: {checklist_name} for user {user_id}")
        
        # Get existing items to avoid duplicates
        existing_items = self.db.query(ChecklistItem.text).filter(
            ChecklistItem.checklist_id == checklist.id
        ).all()
        existing_items = [item[0].lower() for item in existing_items]
        
        # Add new items
        items_added = []
        for item in items:
            if item.lower() not in existing_items:
                checklist_item = ChecklistItem(
                    checklist_id=checklist.id,
                    text=item,
                    is_required=True
                )
                self.db.add(checklist_item)
                items_added.append(item)
                
        if items_added:
            self.db.commit()
            logger.info(f"Added {len(items_added)} items to checklist {checklist_name}")
        
        return {
            "checklist_id": checklist.id,
            "items_added": items_added,
            "items_count": len(items_added)
        } 