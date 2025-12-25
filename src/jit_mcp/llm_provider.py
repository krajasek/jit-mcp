import os
import json
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from pydantic import BaseModel

class IntentResponse(BaseModel):
    needs_tools: bool
    tool_categories: List[str]
    search_query: str
    thought: str

class LLMProvider:
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    async def detect_intent(self, user_query: str, categories: List[str]) -> IntentResponse:
        """
        Detects if the user query needs tools and identifies categories.
        Uses structured output for reliability.
        """
        prompt = f"""
        User Query: {user_query}
        Available Tool Categories: {', '.join(categories)}

        Analyze if this query requires external tools. 
        Return a JSON object with:
        - needs_tools: boolean
        - tool_categories: list of relevant categories from the available list
        - search_query: a specific search string for the tool registry
        - thought: your reasoning process
        """
        
        response = await self.model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=IntentResponse
            )
        )
        return IntentResponse.model_validate_json(response.text)

    async def get_tool_calls(self, user_query: str, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generates tool calls based on the hydrated tools.
        """
        # Note: Gemini 1.5 supports native tool calling, but for JIT we might
        # want to inject them as standard tool definitions.
        
        # Simplified implementation using standard Gemini tool calling
        # In a production system, you'd setup the model with these tools.
        model_with_tools = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            tools=tools
        )
        
        chat = model_with_tools.start_chat()
        response = await chat.send_message_async(user_query)
        
        tool_calls = []
        for part in response.candidates[0].content.parts:
            if part.function_call:
                tool_calls.append({
                    "name": part.function_call.name,
                    "args": dict(part.function_call.args)
                })
        return tool_calls
