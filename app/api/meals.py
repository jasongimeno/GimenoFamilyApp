from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.db.database import get_db
from app.models.user import User
from app.models.meal import Meal
from app.schemas.meal import MealCreate, MealResponse, MealUpdate, MealSearchQuery, MealSuggestionsResponse
from app.utils.auth import get_current_user
from app.core.config import ENABLE_SEARCH

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meals", tags=["Meal Planning"])

# Create a new meal
@router.post("/", response_model=MealResponse, status_code=status.HTTP_201_CREATED)
def create_meal(
    meal_data: MealCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Create meal
    db_meal = Meal(
        user_id=current_user.id,
        name=meal_data.name,
        meal_time=meal_data.meal_time,
        planned_date=meal_data.planned_date,
        details=meal_data.details
    )
    
    # Add to database
    db.add(db_meal)
    db.commit()
    db.refresh(db_meal)
    
    # Index in search service - but don't block if it fails
    try:
        if ENABLE_SEARCH:
            from app.utils.azure_search import index_meal as azure_index_meal
            index_success = azure_index_meal(db_meal)
            if not index_success:
                logger.warning(f"Failed to index meal ID {db_meal.id} in Azure Search, but meal was created in database")
    except Exception as e:
        # If indexing fails, just log the error
        logger.warning(f"Error occurred during meal indexing: {str(e)}")
    
    return db_meal

# Get all meals for the current user
@router.get("/", response_model=List[MealResponse])
def get_meals(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get meals for the current user
    meals = db.query(Meal).filter(
        Meal.user_id == current_user.id
    ).order_by(Meal.planned_date.desc()).offset(skip).limit(limit).all()
    
    return meals

# Get a specific meal
@router.get("/{meal_id}", response_model=MealResponse)
def get_meal(
    meal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get meal
    meal = db.query(Meal).filter(
        Meal.id == meal_id,
        Meal.user_id == current_user.id
    ).first()
    
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )
    
    return meal

# Update a meal
@router.put("/{meal_id}", response_model=MealResponse)
def update_meal(
    meal_id: int,
    meal_data: MealUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get meal
    meal = db.query(Meal).filter(
        Meal.id == meal_id,
        Meal.user_id == current_user.id
    ).first()
    
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )
    
    # Update meal
    meal.name = meal_data.name
    meal.meal_time = meal_data.meal_time
    meal.planned_date = meal_data.planned_date
    meal.details = meal_data.details
    
    db.commit()
    db.refresh(meal)
    
    # Update in search service - but don't block if it fails
    try:
        if ENABLE_SEARCH:
            from app.utils.azure_search import index_meal as azure_index_meal
            index_success = azure_index_meal(meal)
            if not index_success:
                logger.warning(f"Failed to index meal ID {meal.id} in Azure Search during update, but meal was updated in database")
    except Exception as e:
        # If indexing fails, just log the error
        logger.warning(f"Error occurred during meal indexing on update: {str(e)}")
    
    return meal

# Delete a meal
@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal(
    meal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get meal
    meal = db.query(Meal).filter(
        Meal.id == meal_id,
        Meal.user_id == current_user.id
    ).first()
    
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )
    
    # Delete from database
    db.delete(meal)
    db.commit()
    
    # Delete from search service - but don't block if it fails
    try:
        if ENABLE_SEARCH:
            from app.utils.azure_search import delete_document, MEAL_INDEX
            delete_document(MEAL_INDEX, meal_id)
    except Exception as e:
        # If deletion from search service fails, just log the error
        logger.warning(f"Error occurred during meal deletion from search service: {str(e)}")
    
    return None

# Search meals
@router.post("/search", response_model=List[MealResponse])
def search_meal_plans(
    search_query: MealSearchQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    search_results = {"hits": {"hits": []}}
    
    # Use Azure Cognitive Search if enabled
    if ENABLE_SEARCH:
        try:
            from app.utils.azure_search import search_meals as azure_search_meals
            from app.utils.azure_search import search_available
            
            # Check and log if search is available
            logger.info(f"Azure Search available: {search_available}")
            
            # Log the search query
            logger.info(f"Searching meals with query: '{search_query.query}' for user: {current_user.id}")
            
            search_results = azure_search_meals(current_user.id, search_query.query)
            logger.info(f"Using Azure Cognitive Search for meal search with query: {search_query.query}")
            
            # Log search results for debugging
            logger.info(f"Search results: {search_results}")
            
            # If no results, try a fallback database search
            if not search_results["hits"]["hits"]:
                logger.warning(f"No results from Azure Search, trying database fallback")
                return search_meals_in_database(db, current_user.id, search_query.query)
        except ImportError as e:
            logger.warning(f"Azure Cognitive Search module not found: {str(e)}")
            return search_meals_in_database(db, current_user.id, search_query.query)
        except Exception as e:
            logger.error(f"Error using Azure Cognitive Search: {str(e)}", exc_info=True)
            return search_meals_in_database(db, current_user.id, search_query.query)
    else:
        # If search is disabled, use database search
        logger.info("Search is disabled, using database search")
        return search_meals_in_database(db, current_user.id, search_query.query)
    
    # Extract meal IDs
    meal_ids = [hit["_source"]["id"] for hit in search_results["hits"]["hits"]]
    logger.info(f"Found {len(meal_ids)} meal IDs from search")
    
    # Get meals from database
    meals = []
    for meal_id in meal_ids:
        meal = db.query(Meal).filter(Meal.id == meal_id).first()
        if meal:
            meals.append(meal)
    
    logger.info(f"Returning {len(meals)} meals from search")
    return meals

def search_meals_in_database(db, user_id, query, limit=10):
    """Search meals in the database as a fallback when Azure Search is unavailable"""
    logger.info(f"Performing database search for: '{query}'")
    
    # Use a more flexible search by splitting the query into words
    search_terms = query.lower().split()
    
    if not search_terms:
        # If no search terms, return recent meals
        meals = db.query(Meal).filter(
            Meal.user_id == user_id
        ).order_by(Meal.planned_date.desc()).limit(limit).all()
        
        logger.info(f"Empty search term, returning {len(meals)} recent meals")
        return meals
    
    # Build a query that searches for any of the terms in name or details
    from sqlalchemy import or_
    conditions = []
    
    for term in search_terms:
        conditions.append(Meal.name.ilike(f"%{term}%"))
        conditions.append(Meal.details.ilike(f"%{term}%"))
    
    # Get meals that match any of the search terms
    meals = db.query(Meal).filter(
        Meal.user_id == user_id,
        or_(*conditions)
    ).order_by(Meal.planned_date.desc()).limit(limit).all()
    
    logger.info(f"Database search found {len(meals)} meals")
    return meals

# Get meal suggestions based on history
@router.get("/suggestions", response_model=MealSuggestionsResponse)
def get_meal_suggestions(
    current_user: User = Depends(get_current_user)
):
    # In a complete implementation, this would use machine learning to suggest meals
    # based on the user's meal history, preferences, and other factors.
    # For simplicity, we'll just return some placeholder suggestions.
    
    suggestions = [
        {"day": 1, "meal": "Spaghetti and Meatballs"},
        {"day": 2, "meal": "Grilled Chicken Salad"},
        {"day": 3, "meal": "Vegetable Stir Fry"},
        {"day": 4, "meal": "Baked Salmon"},
        {"day": 5, "meal": "Homemade Pizza"},
        {"day": 6, "meal": "Beef Tacos"},
        {"day": 7, "meal": "Roast Chicken with Vegetables"}
    ]
    
    return {"suggestions": suggestions} 