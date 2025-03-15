from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.db.database import get_db
from app.models.user import User
from app.models.meal import Meal
from app.schemas.meal import MealCreate, MealResponse, MealUpdate, MealSearchQuery, MealSuggestionsResponse
from app.utils.auth import get_current_user
from app.utils.elastic import delete_document, MEAL_INDEX, suggest_meal_plan
from app.core.config import ENABLE_ELASTICSEARCH, ENABLE_SEARCH

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
        elif ENABLE_ELASTICSEARCH:
            from app.utils.elastic import index_meal as es_index_meal
            index_success = es_index_meal(db_meal)
            if not index_success:
                logger.warning(f"Failed to index meal ID {db_meal.id} in Elasticsearch, but meal was created in database")
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
    ).order_by(Meal.planned_date).offset(skip).limit(limit).all()
    
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
    
    # Update in Elasticsearch - but don't block if it fails
    try:
        index_success = index_meal(meal)
        if not index_success:
            # Log the failure, but don't halt the process
            print(f"Warning: Failed to index meal ID {meal.id} in Elasticsearch during update, but meal was updated in database")
    except Exception as e:
        # If indexing fails, just log the error
        print(f"Warning: Error occurred during meal indexing on update: {str(e)}")
    
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
    
    # Delete from Elasticsearch - but don't block if it fails
    try:
        delete_document(MEAL_INDEX, meal_id)
    except Exception as e:
        # If deletion from Elasticsearch fails, just log the error
        print(f"Warning: Error occurred during meal deletion from Elasticsearch: {str(e)}")
    
    return None

# Search meals
@router.post("/search", response_model=List[MealResponse])
def search_meal_plans(
    search_query: MealSearchQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    search_results = {"hits": {"hits": []}}
    
    # Try Azure Cognitive Search first if enabled
    if ENABLE_SEARCH:
        try:
            from app.utils.azure_search import search_meals as azure_search_meals
            search_results = azure_search_meals(current_user.id, search_query.query)
            logger.info(f"Using Azure Cognitive Search for meal search with query: {search_query.query}")
        except ImportError:
            logger.warning("Azure Cognitive Search module not found, falling back to Elasticsearch")
        except Exception as e:
            logger.error(f"Error using Azure Cognitive Search: {str(e)}, falling back to Elasticsearch")
    
    # Fallback to Elasticsearch if Azure Search failed or is disabled
    if not search_results["hits"]["hits"] and ENABLE_ELASTICSEARCH:
        try:
            from app.utils.elastic import search_meals as es_search_meals
            search_results = es_search_meals(current_user.id, search_query.query)
            logger.info(f"Using Elasticsearch for meal search with query: {search_query.query}")
        except ImportError:
            logger.warning("Elasticsearch module not found")
        except Exception as e:
            logger.error(f"Error using Elasticsearch: {str(e)}")
    
    # Extract meal IDs
    meal_ids = [hit["_source"]["id"] for hit in search_results["hits"]["hits"]]
    
    # Get meals from database
    meals = []
    for meal_id in meal_ids:
        meal = db.query(Meal).filter(Meal.id == meal_id).first()
        if meal:
            meals.append(meal)
    
    return meals

# Get AI meal suggestions
@router.get("/suggest", response_model=MealSuggestionsResponse)
def get_meal_suggestions(
    current_user: User = Depends(get_current_user)
):
    # Get meal suggestions from Elasticsearch
    suggestions = suggest_meal_plan(current_user.id)
    
    return {"suggestions": suggestions} 