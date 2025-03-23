#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API Client for AutoCodeforge.
This module handles communication with various AI APIs (Claude, DeepSeek, etc).
"""

import os
import json
import logging
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

class BaseAPIClient(ABC):
    """Base abstract class for API clients."""
    
    @abstractmethod
    def send_message(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a message to the API and get the response.
        
        Args:
            prompt: The user prompt to send
            system_prompt: Optional system prompt to set context/behavior
            
        Returns:
            Dict containing the full response from the API
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Dict with model information
        """
        pass


class ClaudeAPIClient(BaseAPIClient):
    """Client for interacting with Claude API."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the Claude API client.
        
        Args:
            api_key: The API key for Claude. If None, will try to get from environment.
            model: The Claude model to use (defaults to claude-3-opus)
        """
        try:
            import anthropic
            self.anthropic_available = True
        except ImportError:
            logger.warning("anthropic package not found. Please install it with: pip install anthropic")
            self.anthropic_available = False
        
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning("No API key provided for Claude. API calls will fail.")
        
        if self.anthropic_available:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.model = model or "claude-3-opus-20240229"  # Default to most capable model
            logger.info(f"Claude API client initialized with model: {self.model}")
        else:
            self.client = None
            self.model = model or "claude-3-opus-20240229"
            logger.warning("Claude API client initialized but anthropic package is missing")
    
    def send_message(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a message to Claude API and get the response.
        
        Args:
            prompt: The user prompt to send to Claude
            system_prompt: Optional system prompt to set context/behavior
            
        Returns:
            Dict containing the full response from Claude API
        """
        if not self.anthropic_available:
            logger.error("Cannot send message: anthropic package is not available")
            raise ImportError("The 'anthropic' package is required to use Claude API. Install with: pip install anthropic")
        
        try:
            logger.info("Sending message to Claude API")
            
            # Create the message request
            messages = [{"role": "user", "content": prompt}]
            
            # Create the request parameters - properly handle system parameter
            request_params = {
                "model": self.model,
                "max_tokens": 4000,
                "messages": messages,
            }
            
            # Only add system parameter if provided
            if system_prompt:
                request_params["system"] = system_prompt
            
            # Send the request
            response = self.client.messages.create(**request_params)
            
            logger.info("Received response from Claude API")
            return response
        
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            raise
    
    def set_model(self, model_name: str) -> None:
        """
        Set the Claude model to use.
        
        Args:
            model_name: Name of the Claude model to use
        """
        self.model = model_name
        logger.info(f"Claude API model set to: {self.model}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Dict with model information
        """
        return {
            "provider": "Claude",
            "model": self.model,
            "capabilities": {
                "max_tokens": 4096,
                "supports_system_prompt": True,
                "supports_json_mode": False
            }
        }


class DeepSeekAPIClient(BaseAPIClient):
    """Client for interacting with DeepSeek API."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the DeepSeek API client.
        
        Args:
            api_key: The API key for DeepSeek. If None, will try to get from environment.
            model: The DeepSeek model to use (defaults to deepseek-chat)
            base_url: The base URL for the DeepSeek API 
        """
        try:
            from openai import OpenAI
            self.openai_available = True
        except ImportError:
            logger.warning("openai package not found. Please install it with: pip install openai")
            self.openai_available = False
        
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            logger.warning("No API key provided for DeepSeek. API calls will fail.")
        
        self.base_url = base_url or "https://api.deepseek.com"
        self.model = model or "deepseek-chat"
        
        if self.openai_available:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            logger.info(f"DeepSeek API client initialized with model: {self.model}")
        else:
            self.client = None
            logger.warning("DeepSeek API client initialized but openai package is missing")
    
    def send_message(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a message to DeepSeek API and get the response.
        
        Args:
            prompt: The user prompt to send to DeepSeek
            system_prompt: Optional system prompt to set context/behavior
            
        Returns:
            Dict containing the full response from DeepSeek API
        """
        if not self.openai_available:
            logger.error("Cannot send message: openai package is not available")
            raise ImportError("The 'openai' package is required to use DeepSeek API. Install with: pip install openai")
        
        try:
            logger.info("Sending message to DeepSeek API")
            
            # Create the messages list
            messages = []
            
            # Add system message if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Add user message
            messages.append({"role": "user", "content": prompt})
            
            # Create the chat completion
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False
            )
            
            logger.info("Received response from DeepSeek API")
            
            # Convert to standard format for our application
            standardized_response = self._standardize_response(response)
            return standardized_response
        
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            raise
    
    def _standardize_response(self, response: Any) -> Dict[str, Any]:
        """
        Standardize the DeepSeek response to match our expected format.
        
        Args:
            response: The raw response from DeepSeek API
            
        Returns:
            Dict with standardized response
        """
        # Extract the text content
        content_text = response.choices[0].message.content
        
        # Create a standardized response structure
        standardized = {
            "content": [
                {
                    "type": "text",
                    "text": content_text
                }
            ],
            "model": self.model,
            "role": "assistant",
            "_original": response  # Keep the original response for reference
        }
        
        return standardized
    
    def set_model(self, model_name: str) -> None:
        """
        Set the DeepSeek model to use.
        
        Args:
            model_name: Name of the DeepSeek model to use
        """
        self.model = model_name
        logger.info(f"DeepSeek API model set to: {self.model}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Dict with model information
        """
        return {
            "provider": "DeepSeek",
            "model": self.model,
            "base_url": self.base_url,
            "capabilities": {
                "max_tokens": 2048,  # Approximate value
                "supports_system_prompt": True,
                "supports_json_mode": False
            }
        }


class MockAPIClient(BaseAPIClient):
    """Mock client for testing without actual API calls."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the mock client.
        
        Args:
            api_key: Not used, included for compatibility
            model: Model name to simulate
        """
        self.api_key = api_key or "mock-api-key"
        self.model = model or "mock-model"
        logger.info("Using mock API client for testing")
    
    def send_message(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Return a mock response."""
        logger.info("Mock: Sending message to API")
        
        # Mock response based on prompt content
        if "hello" in prompt.lower():
            mock_text = "Hello! I'm a mock AI response."
        else:
            mock_text = f"I received your prompt: {prompt[:50]}..."
        
        # Add system prompt influence to the response if provided
        if system_prompt:
            mock_text += f" (Following system instructions: {system_prompt[:20]}...)"
        
        mock_response = {
            "id": "msg_mock12345",
            "content": [
                {
                    "type": "text",
                    "text": mock_text
                }
            ],
            "model": self.model,
            "role": "assistant",
            "stop_reason": "end_turn",
            "type": "message"
        }
        
        logger.info("Mock: Received response from API")
        return mock_response
    
    def set_model(self, model_name: str) -> None:
        """Set the mock model name."""
        self.model = model_name
        logger.info(f"Mock: API model set to: {self.model}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get mock model information."""
        return {
            "provider": "Mock",
            "model": self.model,
            "capabilities": {
                "max_tokens": 1000,
                "supports_system_prompt": True,
                "supports_json_mode": False
            }
        }


def create_api_client(provider: str, api_key: Optional[str] = None, model: Optional[str] = None, **kwargs) -> BaseAPIClient:
    """
    Factory function to create an API client based on the provider.
    
    Args:
        provider: The API provider (claude, deepseek, mock)
        api_key: The API key
        model: The model name
        **kwargs: Additional provider-specific arguments
        
    Returns:
        An API client instance
    """
    provider = provider.lower()
    
    if provider == "claude":
        return ClaudeAPIClient(api_key=api_key, model=model)
    elif provider == "deepseek":
        base_url = kwargs.get("base_url")
        return DeepSeekAPIClient(api_key=api_key, model=model, base_url=base_url)
    elif provider == "mock":
        return MockAPIClient(api_key=api_key, model=model)
    else:
        raise ValueError(f"Unsupported API provider: {provider}")
