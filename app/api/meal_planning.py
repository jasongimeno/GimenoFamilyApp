from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict
import logging
from datetime import datetime

from app.db.database import get_db
from app.utils.auth import get_current_user
from app.services.recipe_parser import RecipeParser
from app.services.checklist_service import ChecklistService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["meal-planning"])

@router.post("/parse-recipe")
async def parse_recipe(
    recipe_text: str = Body(..., embed=True),
    meal_date: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Parse recipe text and add ingredients to weekly shopping list
    """
    try:
        # Convert date string to datetime
        meal_date = datetime.strptime(meal_date, "%Y-%m-%d")
        
        # Parse recipe
        parser = RecipeParser()
        ingredients = parser.parse_recipe_ingredients(recipe_text)
        
        # Get checklist name
        checklist_name = parser.get_weekly_shopping_list_name(meal_date)
        
        # Add ingredients to checklist
        checklist_service = ChecklistService(db)
        result = checklist_service.add_items_to_weekly_checklist(
            user_id=current_user.id,
            checklist_name=checklist_name,
            items=ingredients
        )
        
        return {
            "success": True,
            "checklist_name": checklist_name,
            "ingredients_added": ingredients,
            "checklist_id": result["checklist_id"]
        }
        
    except Exception as e:
        logger.error(f"Error in parse_recipe: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 