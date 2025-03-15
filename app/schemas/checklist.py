from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Checklist Item Schemas
class ChecklistItemBase(BaseModel):
    text: str
    is_required: bool = True

class ChecklistItemCreate(ChecklistItemBase):
    pass

class ChecklistItemUpdate(ChecklistItemBase):
    pass

class ChecklistItemResponse(ChecklistItemBase):
    id: int
    checklist_id: int
    
    class Config:
        from_attributes = True

# Checklist Schemas
class ChecklistBase(BaseModel):
    title: str
    category: Optional[str] = None

class ChecklistCreate(ChecklistBase):
    items: List[ChecklistItemCreate]

class ChecklistUpdate(ChecklistBase):
    items: List[ChecklistItemCreate]

class ChecklistResponse(ChecklistBase):
    id: int
    user_id: int
    created_at: datetime
    items: List[ChecklistItemResponse]
    
    class Config:
        from_attributes = True

# Checklist Run Item Schemas
class ChecklistRunItemBase(BaseModel):
    item_id: int
    completed: bool = False
    notes: Optional[str] = None

class ChecklistRunItemCreate(ChecklistRunItemBase):
    pass

class ChecklistRunItemUpdate(BaseModel):
    completed: bool
    notes: Optional[str] = None

class ChecklistRunItemResponse(ChecklistRunItemBase):
    id: int
    run_id: int
    
    class Config:
        from_attributes = True

# Checklist Run Schemas
class ChecklistRunBase(BaseModel):
    checklist_id: int
    email_sent_to: Optional[str] = None
    notes: Optional[str] = None

class ChecklistRunCreate(ChecklistRunBase):
    pass

class ChecklistRunUpdate(BaseModel):
    completed_at: Optional[datetime] = None
    email_sent_to: Optional[str] = None
    notes: Optional[str] = None

class ChecklistRunResponse(ChecklistRunBase):
    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    run_items: List[ChecklistRunItemResponse]
    
    class Config:
        from_attributes = True

# Complete Checklist Run Request
class CompleteChecklistRunRequest(BaseModel):
    email_sent_to: Optional[str] = None
    notes: Optional[str] = None 