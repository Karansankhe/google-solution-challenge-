import os
import json
import cognee
from app.core.config import get_settings

settings = get_settings()

def init_cognee_env():
    """Ensure Cognee environment variables are set correctly for the underlying library."""
    if settings.COGNEE_API_KEY:
        os.environ["COGNEE_API_KEY"] = settings.COGNEE_API_KEY
    if settings.COGNEE_BASE_URL:
        os.environ["COGNEE_BASE_URL"] = settings.COGNEE_BASE_URL
        
    if settings.LLM_PROVIDER:
        os.environ["LLM_PROVIDER"] = settings.LLM_PROVIDER
    if settings.LLM_MODEL:
        os.environ["LLM_MODEL"] = settings.LLM_MODEL
    if settings.LLM_API_KEY:
        os.environ["LLM_API_KEY"] = settings.LLM_API_KEY
        
    if settings.EMBEDDING_PROVIDER:
        os.environ["EMBEDDING_PROVIDER"] = settings.EMBEDDING_PROVIDER
    if settings.EMBEDDING_MODEL:
        os.environ["EMBEDDING_MODEL"] = settings.EMBEDDING_MODEL
    if settings.COGNEE_SKIP_CONNECTION_TEST:
        os.environ["COGNEE_SKIP_CONNECTION_TEST"] = settings.COGNEE_SKIP_CONNECTION_TEST

async def save_surveillance_report(location: str, report: dict):
    """Save the surveillance report to the Cognee memory graph."""
    init_cognee_env()
    dataset_name = settings.COGNEE_DATASET or "medical_records"
    
    # We add the location inside the report to ensure graph connections
    report_data = {
        "memory_type": "SurveillanceReport",
        "location": location,
        "content": report
    }
    
    # Add to cognee and cognify
    report_text = f"Memory Type: SurveillanceReport\nLocation: {location}\nContent:\n{json.dumps(report, indent=2)}"
    await cognee.add([report_text], dataset_name=dataset_name)
    await cognee.cognify()
    return True

async def retrieve_historical_context(location: str, query: str = "") -> str:
    """Retrieve historical health intelligence for a specific location."""
    init_cognee_env()
    
    if not query:
        query = f"Historical health surges, risks, and outbreaks for {location}"
        
    try:
        # Search for insights related to the location
        results = await cognee.search(
            search_type="insight", 
            query=query
        )
        
        if not results:
            return "No historical memory found for this location."
            
        # Format the results into a string block
        formatted_history = "Historical Context from Memory Graph:\n"
        for idx, res in enumerate(results):
            text_val = str(res)
            formatted_history += f"{idx+1}. {text_val}\n"
            
        return formatted_history
    except Exception as e:
        return f"Warning: Could not retrieve historical context (Error: {str(e)})"
