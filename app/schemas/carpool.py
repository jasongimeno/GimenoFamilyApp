from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Carpool Event Schemas
class CarpoolEventBase(BaseModel):
    description: str
    destination: str
    drop_off_time: datetime
    notes: Optional[str] = None

class CarpoolEventCreate(CarpoolEventBase):
    pass

class CarpoolEventUpdate(CarpoolEventBase):
    pass

class CarpoolEventResponse(CarpoolEventBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Search Query Schema
class CarpoolSearchQuery(BaseModel):
    query: str 