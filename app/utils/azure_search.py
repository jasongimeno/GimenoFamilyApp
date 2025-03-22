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
        # Check if indexes already exist instead of trying to create them
        existing_indexes = [index.name for index in admin_client.list_indexes()]
        
        # Set search_available to True if at least our indexes exist or can be created
        indexes_ready = True
        
        # Check if checklist index exists or needs to be created
        if CHECKLIST_INDEX in existing_indexes:
            logger.info(f"{CHECKLIST_INDEX} already exists")
        else:
            # Check if we're at the index limit
            if len(existing_indexes) >= 3:  # Free tier limit
                logger.warning(f"Cannot create {CHECKLIST_INDEX}: Index quota limit reached (max 3)")
                indexes_ready = False
            else:
                try:
                    # Attempt to create the checklist index
                    checklist_index = SearchIndex(
                        name=CHECKLIST_INDEX,
                        fields=[
                            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
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
                    logger.info(f"Created {CHECKLIST_INDEX} index")
                except Exception as e:
                    indexes_ready = False
                    logger.warning(f"Error creating {CHECKLIST_INDEX} index: {str(e)}")
        
        # Check if carpool index exists or needs to be created
        if CARPOOL_INDEX in existing_indexes:
            logger.info(f"{CARPOOL_INDEX} already exists")
        else:
            # Check if we're at the index limit
            if len(existing_indexes) >= 3:  # Free tier limit
                logger.warning(f"Cannot create {CARPOOL_INDEX}: Index quota limit reached (max 3)")
                indexes_ready = False
            else:
                try:
                    # Attempt to create the carpool index
                    carpool_index = SearchIndex(
                        name=CARPOOL_INDEX,
                        fields=[
                            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                            SimpleField(name="user_id", type=SearchFieldDataType.Int32, filterable=True),
                            SearchableField(name="description", type=SearchFieldDataType.String),
                            SearchableField(name="destination", type=SearchFieldDataType.String),
                            SimpleField(name="drop_off_time", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                            SearchableField(name="notes", type=SearchFieldDataType.String),
                            SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True)
                        ]
                    )
                    admin_client.create_or_update_index(carpool_index)
                    logger.info(f"Created {CARPOOL_INDEX} index")
                except Exception as e:
                    indexes_ready = False
                    logger.warning(f"Error creating {CARPOOL_INDEX} index: {str(e)}")
        
        # Check if meal index exists or needs to be created
        if MEAL_INDEX in existing_indexes:
            logger.info(f"{MEAL_INDEX} already exists")
        else:
            # Check if we're at the index limit
            if len(existing_indexes) >= 3:  # Free tier limit
                logger.warning(f"Cannot create {MEAL_INDEX}: Index quota limit reached (max 3)")
                indexes_ready = False
            else:
                try:
                    # Attempt to create the meal index
                    meal_index = SearchIndex(
                        name=MEAL_INDEX,
                        fields=[
                            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                            SimpleField(name="user_id", type=SearchFieldDataType.Int32, filterable=True),
                            SearchableField(name="name", type=SearchFieldDataType.String),
                            SimpleField(name="meal_time", type=SearchFieldDataType.String, filterable=True),
                            SearchableField(name="details", type=SearchFieldDataType.String),
                            SimpleField(name="planned_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                            SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True)
                        ]
                    )
                    admin_client.create_or_update_index(meal_index)
                    logger.info(f"Created {MEAL_INDEX} index")
                except Exception as e:
                    indexes_ready = False
                    logger.warning(f"Error creating {MEAL_INDEX} index: {str(e)}")
        
        search_available = indexes_ready
        
        if search_available:
            logger.info("Successfully set up Azure Cognitive Search indices")
        else:
            logger.warning("Some Azure Cognitive Search indices could not be created due to quota limits")
            
    except Exception as e:
        search_available = False
        logger.warning(f"Failed to set up Azure Cognitive Search indices: {str(e)}. Search functionality will be disabled.")

# Function to index a checklist document
def index_checklist(checklist, items):
    if not search_available:
        return True  # Return success even if Azure Search is not available
    
    try:
        checklist_doc = {
            "id": str(checklist.id),  # Convert ID to string
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
            "id": str(event.id),  # Convert ID to string
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
            "id": str(meal.id),  # Convert ID to string
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
            client.delete_documents(documents=[{"id": str(doc_id)}])  # Convert ID to string
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
        logger.warning("Azure Search is not available. Returning empty results.")
        return {"hits": {"hits": []}}
    
    try:
        logger.info(f"Performing Azure search for checklists with query: '{query}' for user: {user_id}")
        
        # Log the search client and index information
        if checklist_client:
            logger.info(f"Using checklist_client with index: {checklist_client._index_name}")
        else:
            logger.warning("checklist_client is None - search will fail")
            return {"hits": {"hits": []}}
            
        results = checklist_client.search(
            search_text=query,
            filter=f"user_id eq {user_id}",
            top=size,
            search_mode="all"  # Use 'all' for AND semantics, 'any' for OR semantics
        )
        
        # Log the raw results for debugging
        result_list = list(results)
        logger.info(f"Raw search results count: {len(result_list)}")
        if len(result_list) > 0:
            logger.info(f"First result: {result_list[0] if result_list else 'None'}")
            
        # Try again with more permissive search if no results
        if len(result_list) == 0 and query != "*":
            logger.info(f"No results found, trying wildcard search with '*{query}*'")
            results = checklist_client.search(
                search_text=f"*{query}*",
                filter=f"user_id eq {user_id}",
                top=size
            )
            result_list = list(results)
            logger.info(f"Wildcard search results count: {len(result_list)}")
        
        # Convert to a format compatible with the existing API
        search_results = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "id": int(result["id"]),  # Convert string ID back to integer
                            "user_id": result["user_id"],
                            "title": result["title"],
                            "category": result["category"]
                        }
                    } for result in result_list
                ]
            }
        }
        
        logger.info(f"Returning {len(search_results['hits']['hits'])} checklists from search")
        return search_results
    except Exception as e:
        logger.error(f"Error searching checklists: {str(e)}", exc_info=True)
        return {"hits": {"hits": []}}

# Function to search carpool events
def search_carpool_events(user_id, query, size=10):
    if not search_available:
        logger.warning("Azure Search is not available. Returning empty results.")
        return {"hits": {"hits": []}}
    
    try:
        logger.info(f"Performing Azure search for carpool events with query: '{query}' for user: {user_id}")
        
        # Log the search client and index information
        if carpool_client:
            logger.info(f"Using carpool_client with index: {carpool_client._index_name}")
        else:
            logger.warning("carpool_client is None - search will fail")
            return {"hits": {"hits": []}}
            
        results = carpool_client.search(
            search_text=query,
            filter=f"user_id eq {user_id}",
            top=size,
            search_mode="all"  # Use 'all' for AND semantics, 'any' for OR semantics
        )
        
        # Log the raw results for debugging
        result_list = list(results)
        logger.info(f"Raw search results count: {len(result_list)}")
        if len(result_list) > 0:
            logger.info(f"First result: {result_list[0] if result_list else 'None'}")
            
        # Try again with more permissive search if no results
        if len(result_list) == 0 and query != "*":
            logger.info(f"No results found, trying wildcard search with '*{query}*'")
            results = carpool_client.search(
                search_text=f"*{query}*",
                filter=f"user_id eq {user_id}",
                top=size
            )
            result_list = list(results)
            logger.info(f"Wildcard search results count: {len(result_list)}")
        
        # Convert to a format compatible with the existing API
        search_results = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "id": int(result["id"]),  # Convert string ID back to integer
                            "user_id": result["user_id"],
                            "description": result["description"],
                            "destination": result["destination"]
                        }
                    } for result in result_list
                ]
            }
        }
        
        logger.info(f"Returning {len(search_results['hits']['hits'])} carpool events from search")
        return search_results
    except Exception as e:
        logger.error(f"Error searching carpool events: {str(e)}", exc_info=True)
        return {"hits": {"hits": []}}

# Function to search meals
def search_meals(user_id, query, size=10):
    if not search_available:
        logger.warning("Azure Search is not available. Returning empty results.")
        return {"hits": {"hits": []}}
    
    try:
        logger.info(f"Performing Azure search for meals with query: '{query}' for user: {user_id}")
        
        # Log the search client and index information
        if meal_client:
            logger.info(f"Using meal_client with index: {meal_client._index_name}")
        else:
            logger.warning("meal_client is None - search will fail")
            return {"hits": {"hits": []}}
            
        results = meal_client.search(
            search_text=query,
            filter=f"user_id eq {user_id}",
            top=size,
            search_mode="all"  # Use 'all' for AND semantics, 'any' for OR semantics
        )
        
        # Log the raw results for debugging
        result_list = list(results)
        logger.info(f"Raw search results count: {len(result_list)}")
        if len(result_list) > 0:
            logger.info(f"First result: {result_list[0] if result_list else 'None'}")
            
        # Try again with more permissive search if no results
        if len(result_list) == 0 and query != "*":
            logger.info(f"No results found, trying wildcard search with '*{query}*'")
            results = meal_client.search(
                search_text=f"*{query}*",
                filter=f"user_id eq {user_id}",
                top=size
            )
            result_list = list(results)
            logger.info(f"Wildcard search results count: {len(result_list)}")
        
        # Convert to a format compatible with the existing API
        search_results = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "id": int(result["id"]),  # Convert string ID back to integer
                            "user_id": result["user_id"],
                            "name": result["name"],
                            "meal_time": result["meal_time"]
                        }
                    } for result in result_list
                ]
            }
        }
        
        logger.info(f"Returning {len(search_results['hits']['hits'])} meals from search")
        return search_results
    except Exception as e:
        logger.error(f"Error searching meals: {str(e)}", exc_info=True)
        return {"hits": {"hits": []}}

# Function to suggest meals based on historical data
def suggest_meal_plan(user_id):
    if not search_available:
        return []
    
    try:
        # Get historical meals (all meals for this user)
        results = meal_client.search(
            search_text="*",
            filter=f"user_id eq {user_id}",
            top=1000
        )
        
        # Process results to generate suggestions
        # (In a real app, we would implement more sophisticated AI algorithms here)
        meals = [result["name"] for result in results]
        
        # Simple frequency-based suggestion
        from collections import Counter
        meal_counts = Counter(meals)
        common_meals = meal_counts.most_common(7)  # Get top 7 meals
        
        return [{"day": i+1, "meal": meal[0]} for i, meal in enumerate(common_meals)] if common_meals else []
    except Exception as e:
        logger.error(f"Error suggesting meals: {str(e)}")
        return []

# Diagnostic function to get search status
def get_search_diagnostic_info():
    """Return diagnostic information about search service status"""
    if not ENABLE_SEARCH or not SEARCH_API_KEY:
        return {
            "search_enabled": ENABLE_SEARCH,
            "api_key_provided": bool(SEARCH_API_KEY),
            "status": "Search is disabled in configuration"
        }
    
    try:
        existing_indexes = [index.name for index in admin_client.list_indexes()]
        
        # Check which of our required indexes exist
        required_indexes = {
            CHECKLIST_INDEX: CHECKLIST_INDEX in existing_indexes,
            CARPOOL_INDEX: CARPOOL_INDEX in existing_indexes,
            MEAL_INDEX: MEAL_INDEX in existing_indexes
        }
        
        # Get document counts for existing indexes
        doc_counts = {}
        index_issues = {}
        
        for index_name in existing_indexes:
            try:
                # Get the appropriate client
                client = None
                if index_name == CHECKLIST_INDEX:
                    client = checklist_client
                elif index_name == CARPOOL_INDEX:
                    client = carpool_client
                elif index_name == MEAL_INDEX:
                    client = meal_client
                
                if client:
                    # Try to get document count
                    try:
                        results = client.search(search_text="*", top=1)
                        doc_counts[index_name] = results.get_count()
                    except Exception as e:
                        doc_counts[index_name] = f"Error counting documents: {str(e)}"
                        index_issues[index_name] = {
                            "count_error": str(e)
                        }
                        
                    # Try a simple query to test if search works
                    try:
                        test_results = client.search(search_text="test", top=1)
                        sample_count = len(list(test_results))
                        index_issues[index_name] = index_issues.get(index_name, {})
                        index_issues[index_name]["test_query"] = {
                            "success": True,
                            "results": sample_count
                        }
                    except Exception as e:
                        index_issues[index_name] = index_issues.get(index_name, {})
                        index_issues[index_name]["test_query"] = {
                            "success": False,
                            "error": str(e)
                        }
            except Exception as e:
                doc_counts[index_name] = f"Error accessing index: {str(e)}"
                index_issues[index_name] = {
                    "general_error": str(e)
                }
            
        return {
            "search_enabled": ENABLE_SEARCH,
            "search_available": search_available,
            "service_name": SEARCH_SERVICE_NAME,
            "endpoint": endpoint,
            "all_indexes": existing_indexes,
            "required_indexes_status": required_indexes,
            "document_counts": doc_counts,
            "index_issues": index_issues,
            "search_index_prefix": SEARCH_INDEX_PREFIX
        }
    except Exception as e:
        return {
            "search_enabled": ENABLE_SEARCH,
            "search_available": search_available,
            "service_name": SEARCH_SERVICE_NAME,
            "endpoint": endpoint,
            "error": f"Error getting diagnostic info: {str(e)}"
        } 