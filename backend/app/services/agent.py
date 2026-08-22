from google import genai
from app.core.config import get_settings
from app.models.chat import ChatRequest

settings = get_settings()

client = genai.Client(api_key=settings.GEMINI_API_KEY)

async def generate_agent_response(request: ChatRequest) -> str:
    # Prepare messages
    # The new google-genai SDK uses a specific format, for simplicity here we just
    # concatenate the conversation history if any.
    # In a full production app, you would map 'user'/'model' roles appropriately.
    
    contents = []
    if request.system_prompt:
        contents.append(f"System: {request.system_prompt}")
        
    for msg in request.messages:
        contents.append(f"{msg.role}: {msg.content}")
        
    prompt = "\n".join(contents)
    
    # We use gemini-2.5-flash as the default model
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    return response.text
