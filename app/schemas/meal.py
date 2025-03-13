from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime

# Meal Schemas
class MealBase(BaseModel):
    name: str
    meal_time: str
    planned_date: date
    details: Optional[str] = None

class MealCreate(MealBase):
    pass

class MealUpdate(MealBase):
    pass

class MealResponse(MealBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Meal Suggestion Schemas
class MealSuggestion(BaseModel):
    day: int
    meal: str

class MealSuggestionsResponse(BaseModel):
    suggestions: List[MealSuggestion]

# Search Query Schema
class MealSearchQuery(BaseModel):
    query: str 