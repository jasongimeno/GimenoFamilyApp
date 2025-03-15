from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, 
    SimpleField, 
    SearchableField,
    SearchFieldDataType,
    ComplexField
)
import logging
import os
from app.core.config import (
    ENABLE_SEARCH, 
    SEARCH_SERVICE_NAME, 
    SEARCH_API_KEY, 
    SEARCH_INDEX_PREFIX, 
)

# Set up logging
logger = logging.getLogger(__name__)

# Track if Azure Search is available
search_available = False

# Azure Search service endpoint
endpoint = f"https://{SEARCH_SERVICE_NAME}.search.windows.net"

# Index names
CHECKLIST_INDEX = f"{SEARCH_INDEX_PREFIX}-checklists"
CARPOOL_INDEX = f"{SEARCH_INDEX_PREFIX}-carpool"
MEAL_INDEX = f"{SEARCH_INDEX_PREFIX}-meals"

# Initialize Azure Search clients if enabled
if ENABLE_SEARCH and SEARCH_API_KEY:
    try:
        admin_client = SearchIndexClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(SEARCH_API_KEY)
        )
        
        # Create client instances for each index
        checklist_client = SearchClient(
            endpoint=endpoint, 
            index_name=CHECKLIST_INDEX,
            credential=AzureKeyCredential(SEARCH_API_KEY)
        )
        
        carpool_client = SearchClient(
            endpoint=endpoint, 
            index_name=CARPOOL_INDEX,
            credential=AzureKeyCredential(SEARCH_API_KEY)
        )
        
        meal_client = SearchClient(
            endpoint=endpoint, 
            index_name=MEAL_INDEX,
            credential=AzureKeyCredential(SEARCH_API_KEY)
        )
        
        search_available = True
        logger.info(f"Azure Cognitive Search clients initialized for service: {SEARCH_SERVICE_NAME}")
    except Exception as e:
        logger.error(f"Failed to initialize Azure Cognitive Search: {str(e)}")
        search_available = False
else:
    admin_client = None
    checklist_client = None
    carpool_client = None
    meal_client = None
    logger.info("Azure Cognitive Search is disabled in configuration. Search functionality will be disabled.")

# Function to create or update indices
def setup_azure_search_indices():
    global search_available
    
    # Skip if Azure Search is disabled
    if not ENABLE_SEARCH or not SEARCH_API_KEY:
        search_available = False
        logger.info("Azure Search is disabled. Skipping index setup.")
        return
    
    try:
        # Attempt to create the checklist index
        try:
            checklist_index = SearchIndex(
                name=CHECKLIST_INDEX,
                fields=[
                    SimpleField(name="id", type=SearchFieldDataType.Int32, key=True),
                    SimpleField(name="user_id", type=SearchFieldDataType.Int32, filterable=True),
                    SearchableField(name="title", type=SearchFieldDataType.String),
                    SimpleField(name="category", type=SearchFieldDataType.String, filterable=True),
                    ComplexField(name="items", fields=[
                        SearchableField(name="text", type=SearchFieldDataType.String),
                        SimpleField(name="required", type=SearchFieldDataType.Boolean)
                    ]),
                    SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True)
                ]
            )
            admin_client.create_or_update_index(checklist_index)
            logger.info(f"Created or updated {CHECKLIST_INDEX} index")
        except Exception as e:
            logger.warning(f"Error creating {CHECKLIST_INDEX} index: {str(e)}")

        # Attempt to create the carpool index
        try:
            carpool_index = SearchIndex(
                name=CARPOOL_INDEX,
                fields=[
                    SimpleField(name="id", type=SearchFieldDataType.Int32, key=True),
                    SimpleField(name="user_id", type=SearchFieldDataType.Int32, filterable=True),
                    SearchableField(name="description", type=SearchFieldDataType.String),
                    SearchableField(name="destination", type=SearchFieldDataType.String),
                    SimpleField(name="drop_off_time", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                    SearchableField(name="notes", type=SearchFieldDataType.String),
                    SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True)
                ]
            )
            admin_client.create_or_update_index(carpool_index)
            logger.info(f"Created or updated {CARPOOL_INDEX} index")
        except Exception as e:
            logger.warning(f"Error creating {CARPOOL_INDEX} index: {str(e)}")

        # Attempt to create the meal index
        try:
            meal_index = SearchIndex(
                name=MEAL_INDEX,
                fields=[
                    SimpleField(name="id", type=SearchFieldDataType.Int32, key=True),
                    SimpleField(name="user_id", type=SearchFieldDataType.Int32, filterable=True),
                    SearchableField(name="name", type=SearchFieldDataType.String),
                    SimpleField(name="meal_time", type=SearchFieldDataType.String, filterable=True),
                    SearchableField(name="details", type=SearchFieldDataType.String),
                    SimpleField(name="planned_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                    SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True)
                ]
            )
            admin_client.create_or_update_index(meal_index)
            logger.info(f"Created or updated {MEAL_INDEX} index")
        except Exception as e:
            logger.warning(f"Error creating {MEAL_INDEX} index: {str(e)}")
        
        search_available = True
        logger.info("Successfully set up Azure Cognitive Search indices")
    except Exception as e:
        search_available = False
        logger.warning(f"Failed to set up Azure Cognitive Search indices: {str(e)}. Search functionality will be disabled.")

# Function to index a checklist document
def index_checklist(checklist, items):
    if not search_available:
        return True  # Return success even if Azure Search is not available
    
    try:
        checklist_doc = {
            "id": checklist.id,
            "user_id": checklist.user_id,
            "title": checklist.title,
            "category": checklist.category,
            "items": [{"text": item.text, "required": item.is_required} for item in items],
            "created_at": checklist.created_at.isoformat() if checklist.created_at else None
        }
        
        checklist_client.upload_documents(documents=[checklist_doc])
        return True  # Successful indexing
    except Exception as e:
        logger.error(f"Error indexing checklist: {str(e)}")
        return False  # Failed indexing, but don't halt the application

# Function to index a carpool event document
def index_carpool_event(event):
    if not search_available:
        return True  # Return success even if Azure Search is not available
    
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
        
        carpool_client.upload_documents(documents=[event_doc])
        return True  # Successful indexing
    except Exception as e:
        logger.error(f"Error indexing carpool event: {str(e)}")
        return False  # Failed indexing, but don't halt the application

# Function to index a meal document
def index_meal(meal):
    if not search_available:
        return True  # Return success even if Azure Search is not available
    
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
        
        meal_client.upload_documents(documents=[meal_doc])
        return True  # Successful indexing
    except Exception as e:
        logger.error(f"Error indexing meal: {str(e)}")
        return False  # Failed indexing, but don't halt the application

# Function to delete a document from an index
def delete_document(index, doc_id):
    if not search_available:
        return True  # Return success even if Azure Search is not available
    
    try:
        client = None
        if index == CHECKLIST_INDEX:
            client = checklist_client
        elif index == CARPOOL_INDEX:
            client = carpool_client
        elif index == MEAL_INDEX:
            client = meal_client
        
        if client:
            client.delete_documents(documents=[{"id": doc_id}])
            return True  # Successful deletion
        else:
            logger.error(f"No client available for index {index}")
            return False
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        return False  # Failed deletion, but don't halt the application

# Function to search checklists
def search_checklists(user_id, query, size=10):
    if not search_available:
        return {"results": []}
    
    try:
        results = checklist_client.search(
            search_text=query,
            filter=f"user_id eq {user_id}",
            top=size
        )
        
        # Convert to a format compatible with the existing API
        search_results = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "id": result["id"],
                            "user_id": result["user_id"],
                            "title": result["title"],
                            "category": result["category"]
                        }
                    } for result in results
                ]
            }
        }
        
        return search_results
    except Exception as e:
        logger.error(f"Error searching checklists: {str(e)}")
        return {"hits": {"hits": []}}

# Function to search carpool events
def search_carpool_events(user_id, query, size=10):
    if not search_available:
        return {"hits": {"hits": []}}
    
    try:
        results = carpool_client.search(
            search_text=query,
            filter=f"user_id eq {user_id}",
            top=size
        )
        
        # Convert to a format compatible with the existing API
        search_results = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "id": result["id"],
                            "user_id": result["user_id"],
                            "description": result["description"],
                            "destination": result["destination"]
                        }
                    } for result in results
                ]
            }
        }
        
        return search_results
    except Exception as e:
        logger.error(f"Error searching carpool events: {str(e)}")
        return {"hits": {"hits": []}}

# Function to search meals
def search_meals(user_id, query, size=10):
    if not search_available:
        return {"hits": {"hits": []}}
    
    try:
        results = meal_client.search(
            search_text=query,
            filter=f"user_id eq {user_id}",
            top=size
        )
        
        # Convert to a format compatible with the existing API
        search_results = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "id": result["id"],
                            "user_id": result["user_id"],
                            "name": result["name"],
                            "meal_time": result["meal_time"],
                            "details": result["details"]
                        }
                    } for result in results
                ]
            }
        }
        
        return search_results
    except Exception as e:
        logger.error(f"Error searching meals: {str(e)}")
        return {"hits": {"hits": []}} 