from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError
import logging
from app.core.config import ELASTICSEARCH_HOST, ELASTICSEARCH_API_KEY, ELASTICSEARCH_INDEX_PREFIX, ENABLE_ELASTICSEARCH

# Set up logging
logger = logging.getLogger(__name__)

# Track if Elasticsearch is available
elasticsearch_available = False

# Initialize Elasticsearch client if enabled
if ENABLE_ELASTICSEARCH:
    es_client = Elasticsearch(
        ELASTICSEARCH_HOST,
        api_key=ELASTICSEARCH_API_KEY if ELASTICSEARCH_API_KEY else None
    )
else:
    es_client = None
    logger.info("Elasticsearch is disabled in configuration. Search functionality will be disabled.")

# Index names
CHECKLIST_INDEX = f"{ELASTICSEARCH_INDEX_PREFIX}-checklists"
CARPOOL_INDEX = f"{ELASTICSEARCH_INDEX_PREFIX}-carpool"
MEAL_INDEX = f"{ELASTICSEARCH_INDEX_PREFIX}-meals"

# Function to create or update indices
def setup_elasticsearch_indices():
    global elasticsearch_available
    
    # Skip if Elasticsearch is disabled
    if not ENABLE_ELASTICSEARCH:
        elasticsearch_available = False
        logger.info("Elasticsearch is disabled. Skipping index setup.")
        return
    
    try:
        # Check if Elasticsearch is available with timeout
        if es_client.ping(request_timeout=5):
            elasticsearch_available = True
            logger.info("Successfully connected to Elasticsearch")
            
            try:
                # Checklist index
                if not es_client.indices.exists(index=CHECKLIST_INDEX):
                    es_client.indices.create(
                        index=CHECKLIST_INDEX,
                        body={
                            "mappings": {
                                "properties": {
                                    "id": {"type": "integer"},
                                    "user_id": {"type": "integer"},
                                    "title": {"type": "text"},
                                    "category": {"type": "keyword"},
                                    "items": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "text"},
                                            "required": {"type": "boolean"}
                                        }
                                    },
                                    "created_at": {"type": "date"}
                                }
                            }
                        }
                    )
                    logger.info(f"Created {CHECKLIST_INDEX} index")
            except Exception as e:
                logger.warning(f"Error creating {CHECKLIST_INDEX} index: {str(e)}")

            try:
                # Carpool index
                if not es_client.indices.exists(index=CARPOOL_INDEX):
                    es_client.indices.create(
                        index=CARPOOL_INDEX,
                        body={
                            "mappings": {
                                "properties": {
                                    "id": {"type": "integer"},
                                    "user_id": {"type": "integer"},
                                    "description": {"type": "text"},
                                    "destination": {"type": "text"},
                                    "drop_off_time": {"type": "date"},
                                    "notes": {"type": "text"},
                                    "created_at": {"type": "date"}
                                }
                            }
                        }
                    )
                    logger.info(f"Created {CARPOOL_INDEX} index")
            except Exception as e:
                logger.warning(f"Error creating {CARPOOL_INDEX} index: {str(e)}")

            try:
                # Meal index
                if not es_client.indices.exists(index=MEAL_INDEX):
                    es_client.indices.create(
                        index=MEAL_INDEX,
                        body={
                            "mappings": {
                                "properties": {
                                    "id": {"type": "integer"},
                                    "user_id": {"type": "integer"},
                                    "name": {"type": "text"},
                                    "meal_time": {"type": "keyword"},
                                    "details": {"type": "text"},
                                    "planned_date": {"type": "date"},
                                    "created_at": {"type": "date"}
                                }
                            }
                        }
                    )
                    logger.info(f"Created {MEAL_INDEX} index")
            except Exception as e:
                logger.warning(f"Error creating {MEAL_INDEX} index: {str(e)}")
        else:
            elasticsearch_available = False
            logger.warning("Elasticsearch is not available. Search functionality will be disabled.")
    except (ESConnectionError, Exception) as e:
        elasticsearch_available = False
        logger.warning(f"Failed to connect to Elasticsearch: {str(e)}. Search functionality will be disabled.")

# Function to index a checklist document
def index_checklist(checklist, items):
    if not elasticsearch_available:
        return True  # Return success even if Elasticsearch is not available
    
    try:
        checklist_doc = {
            "id": checklist.id,
            "user_id": checklist.user_id,
            "title": checklist.title,
            "category": checklist.category,
            "items": [{"text": item.text, "required": item.is_required} for item in items],
            "created_at": checklist.created_at.isoformat() if checklist.created_at else None
        }
        
        es_client.index(
            index=CHECKLIST_INDEX,
            id=checklist.id,
            document=checklist_doc
        )
        return True  # Successful indexing
    except Exception as e:
        logger.error(f"Error indexing checklist: {str(e)}")
        return False  # Failed indexing, but don't halt the application

# Function to index a carpool event document
def index_carpool_event(event):
    if not elasticsearch_available:
        return True  # Return success even if Elasticsearch is not available
    
    try:
        event_doc = {
            "id": event.id,
            "user_id": event.user_id,
            "description": event.description,
            "destination": event.destination,
            "drop_off_time": event.drop_off_time.isoformat() if event.drop_off_time else None,
            "notes": event.notes,
            "created_at": event.created_at.isoformat() if event.created_at else None
        }
        
        es_client.index(
            index=CARPOOL_INDEX,
            id=event.id,
            document=event_doc
        )
        return True  # Successful indexing
    except Exception as e:
        logger.error(f"Error indexing carpool event: {str(e)}")
        return False  # Failed indexing, but don't halt the application

# Function to index a meal document
def index_meal(meal):
    if not elasticsearch_available:
        return True  # Return success even if Elasticsearch is not available
    
    try:
        meal_doc = {
            "id": meal.id,
            "user_id": meal.user_id,
            "name": meal.name,
            "meal_time": meal.meal_time,
            "details": meal.details,
            "planned_date": meal.planned_date.isoformat() if meal.planned_date else None,
            "created_at": meal.created_at.isoformat() if meal.created_at else None
        }
        
        es_client.index(
            index=MEAL_INDEX,
            id=meal.id,
            document=meal_doc
        )
        return True  # Successful indexing
    except Exception as e:
        logger.error(f"Error indexing meal: {str(e)}")
        return False  # Failed indexing, but don't halt the application

# Function to delete a document from an index
def delete_document(index, doc_id):
    if not elasticsearch_available:
        return True  # Return success even if Elasticsearch is not available
    
    try:
        es_client.delete(index=index, id=doc_id)
        return True  # Successful deletion
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        return False  # Failed deletion, but don't halt the application

# Function to search checklists
def search_checklists(user_id, query, size=10):
    if not elasticsearch_available:
        return {"hits": {"hits": []}}
    
    try:
        body = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"user_id": user_id}},
                        {"multi_match": {
                            "query": query,
                            "fields": ["title", "category", "items.text"]
                        }}
                    ]
                }
            },
            "size": size
        }
        
        return es_client.search(index=CHECKLIST_INDEX, body=body)
    except Exception as e:
        logger.error(f"Error searching checklists: {str(e)}")
        return {"hits": {"hits": []}}

# Function to search carpool events
def search_carpool_events(user_id, query, size=10):
    if not elasticsearch_available:
        return {"hits": {"hits": []}}
    
    try:
        body = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"user_id": user_id}},
                        {"multi_match": {
                            "query": query,
                            "fields": ["description", "destination", "notes"]
                        }}
                    ]
                }
            },
            "size": size
        }
        
        return es_client.search(index=CARPOOL_INDEX, body=body)
    except Exception as e:
        logger.error(f"Error searching carpool events: {str(e)}")
        return {"hits": {"hits": []}}

# Function to search meals
def search_meals(user_id, query, size=10):
    if not elasticsearch_available:
        return {"hits": {"hits": []}}
    
    try:
        body = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"user_id": user_id}},
                        {"multi_match": {
                            "query": query,
                            "fields": ["name", "details", "meal_time"]
                        }}
                    ]
                }
            },
            "size": size
        }
        
        return es_client.search(index=MEAL_INDEX, body=body)
    except Exception as e:
        logger.error(f"Error searching meals: {str(e)}")
        return {"hits": {"hits": []}}

# Function to suggest meals based on historical data
def suggest_meal_plan(user_id):
    if not elasticsearch_available:
        return []
    
    try:
        # Get historical meals
        body = {
            "query": {
                "term": {"user_id": user_id}
            },
            "size": 1000
        }
        
        results = es_client.search(index=MEAL_INDEX, body=body)
        
        # Process results to generate suggestions
        # (In a real app, we would implement more sophisticated AI algorithms here)
        meals = [hit["_source"]["name"] for hit in results["hits"]["hits"]]
        
        # Simple frequency-based suggestion
        from collections import Counter
        meal_counts = Counter(meals)
        common_meals = meal_counts.most_common(7)  # Get top 7 meals
        
        return [{"day": i+1, "meal": meal[0]} for i, meal in enumerate(common_meals)] if common_meals else []
    except Exception as e:
        logger.error(f"Error suggesting meals: {str(e)}")
        return [] 