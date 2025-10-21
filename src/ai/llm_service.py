from __future__ import annotations
import asyncio
import json
from typing import Optional
import requests

from .config import settings

class LLMService:
    """LLM service adapter that supports Ollama API calls"""
    
    def __init__(self):
        """Initialize LLM service with Ollama configuration"""
        if not settings.OLLAMA_HOST or not settings.OLLAMA_MODEL:
            raise ValueError("OLLAMA_HOST and OLLAMA_MODEL must be configured")
        self.host = str(settings.OLLAMA_HOST).rstrip("/")
        self.model = settings.OLLAMA_MODEL
        
    async def generate(self, prompt: str, max_tokens: Optional[int] = None, 
                      temperature: Optional[float] = None) -> str:
        """
        Generate text from Ollama API
        
        Args:
            prompt: Input text to generate from
            max_tokens: Maximum tokens to generate (default from settings)
            temperature: Generation temperature (default from settings)
            
        Returns:
            Generated text response
            
        Raises:
            RuntimeError: If Ollama API call fails
        """
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,  # Disable streaming for simpler response handling
            "options": {
                "temperature": temperature if temperature is not None else settings.TEMPERATURE,
                "num_predict": max_tokens or settings.MAX_TOKENS
            }
        }
        
        try:
            # Make API call in thread pool to avoid blocking
            response = await asyncio.to_thread(
                requests.post,
                url,
                json=payload,
                timeout=settings.TIMEOUT_SECONDS
            )
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            # Ollama non-streaming response format
            if isinstance(data, dict) and "response" in data:
                return data["response"].strip()
            
            # Fallback
            return json.dumps(data)
            
        except requests.exceptions.JSONDecodeError as e:
            # If we still get streaming response, parse line by line
            try:
                lines = response.text.strip().split('\n')
                full_response = []
                for line in lines:
                    if line:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            full_response.append(chunk["response"])
                return "".join(full_response).strip()
            except Exception as parse_error:
                raise RuntimeError(f"Failed to parse Ollama response: {parse_error}") from parse_error
        except Exception as e:
            raise RuntimeError(f"Ollama API call failed: {str(e)}") from e
    
    async def health_check(self) -> bool:
        """
        Check if Ollama API is responsive
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            url = f"{self.host}/api/tags"
            response = await asyncio.to_thread(
                requests.get,
                url,
                timeout=5
            )
            response.raise_for_status()
            return True
        except Exception:
            return False