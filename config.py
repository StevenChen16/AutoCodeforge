#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration module for AutoCodeforge.
Handles loading and validation of configuration.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "api": {
        "default_provider": "claude",
        "providers": {
            "claude": {
                "api_key": "",
                "model": "claude-3-opus-20240229",
                "max_tokens": 4000
            },
            "deepseek": {
                "api_key": "",
                "model": "deepseek-chat",
                "base_url": "https://api.deepseek.com",
                "max_tokens": 2048
            },
            "mock": {
                "model": "mock-model"
            }
        }
    },
    "file_manager": {
        "base_path": os.path.abspath(os.path.join(os.path.dirname(__file__), "work")),
        "project_subdirs": True
    },
    "shell_executor": {
        "timeout": 300,
        "allow_network_access": True
    },
    "cycle": {
        "max_iterations": 5,
        "stop_on_error": False
    },
    "system_prompt": {
        "include_code_context": True,
        "include_directory_structure": True,
        "suggest_test_data": True
    }
}

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the config file
        
    Returns:
        Configuration dictionary
    """
    config = DEFAULT_CONFIG.copy()
    
    # Try to load config from file
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            
            # Update default config with file config
            deep_update(config, file_config)
            logger.info(f"Configuration loaded from {config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration from {config_path}: {e}")
            logger.info("Using default configuration")
    else:
        logger.warning(f"Configuration file {config_path} not found, using default configuration")
        
        # Create default config file for future use
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Default configuration saved to {config_path}")
        except Exception as e:
            logger.warning(f"Could not save default configuration to {config_path}: {e}")
    
    # Check for environment variables for API keys
    if "ANTHROPIC_API_KEY" in os.environ:
        config["api"]["providers"]["claude"]["api_key"] = os.environ["ANTHROPIC_API_KEY"]
        logger.info("Using Claude API key from environment variable")
    
    if "DEEPSEEK_API_KEY" in os.environ:
        config["api"]["providers"]["deepseek"]["api_key"] = os.environ["DEEPSEEK_API_KEY"]
        logger.info("Using DeepSeek API key from environment variable")
    
    # Special handling for OpenAI API key (some may use this for DeepSeek)
    if "OPENAI_API_KEY" in os.environ and not config["api"]["providers"]["deepseek"]["api_key"]:
        config["api"]["providers"]["deepseek"]["api_key"] = os.environ["OPENAI_API_KEY"]
        logger.info("Using OpenAI API key for DeepSeek from environment variable")
    
    validate_config(config)
    return config

def get_api_config(config: Dict[str, Any], provider: Optional[str] = None) -> Dict[str, Any]:
    """
    Get API configuration for a specific provider.
    
    Args:
        config: Full configuration dictionary
        provider: Provider name (if None, use default provider)
        
    Returns:
        API configuration for the specified provider
    """
    if provider is None:
        provider = config["api"].get("default_provider", "claude")
    
    # Get provider config or default to empty dict if provider doesn't exist
    provider_config = config["api"].get("providers", {}).get(provider, {})
    
    # Add provider name to the config for reference
    provider_config["provider"] = provider
    
    return provider_config

def get_project_path(config: Dict[str, Any], project_name: str) -> str:
    """
    Get the path for a specific project.
    
    Args:
        config: Configuration dictionary
        project_name: Name of the project
        
    Returns:
        Absolute path to the project directory
    """
    base_path = config["file_manager"]["base_path"]
    
    if config["file_manager"].get("project_subdirs", True):
        # Sanitize project name for use as directory name
        safe_name = sanitize_project_name(project_name)
        project_path = os.path.join(base_path, safe_name)
    else:
        project_path = base_path
    
    # Ensure the directory exists
    os.makedirs(project_path, exist_ok=True)
    
    return project_path

def sanitize_project_name(project_name: str) -> str:
    """
    Sanitize project name for use as directory name.
    
    Args:
        project_name: Raw project name
        
    Returns:
        Sanitized name safe for use as directory name
    """
    # Replace spaces with underscores and remove invalid characters
    safe_name = project_name.strip().lower()
    safe_name = safe_name.replace(" ", "_")
    
    # Keep only alphanumeric characters, underscore, and hyphen
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "_-")
    
    # Ensure the name isn't empty
    if not safe_name:
        safe_name = "project"
        
    # Limit length
    if len(safe_name) > 50:
        safe_name = safe_name[:50]
    
    return safe_name

def deep_update(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep update of nested dictionaries.
    
    Args:
        target: Target dictionary to update
        source: Source dictionary with values to update
        
    Returns:
        Updated target dictionary
    """
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            deep_update(target[key], value)
        else:
            target[key] = value
    return target

def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate configuration.
    
    Args:
        config: Configuration dictionary to validate
    """
    # Check required fields
    if not config.get("file_manager", {}).get("base_path"):
        config["file_manager"]["base_path"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "work"))
        logger.warning("Base path not configured, setting to 'work' directory")
    
    # Sanitize paths
    config["file_manager"]["base_path"] = os.path.abspath(config["file_manager"]["base_path"])
    
    # Validate timeout value
    if config.get("shell_executor", {}).get("timeout", 0) <= 0:
        config["shell_executor"]["timeout"] = 300
        logger.warning("Invalid timeout value, setting to default (300 seconds)")
    
    # Ensure default provider exists
    default_provider = config["api"].get("default_provider", "claude")
    if default_provider not in config["api"].get("providers", {}):
        logger.warning(f"Default provider '{default_provider}' not configured, falling back to 'mock'")
        config["api"]["default_provider"] = "mock"
    
    # Warn about missing API keys
    for provider, provider_config in config["api"].get("providers", {}).items():
        if provider in ["claude", "deepseek"] and not provider_config.get("api_key"):
            logger.warning(f"No API key configured for provider '{provider}'. API calls will fail unless provided through environment.")
    
    logger.info("Configuration validated")

def list_available_providers(config: Dict[str, Any]) -> List[str]:
    """
    List available API providers from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of available provider names
    """
    return list(config["api"].get("providers", {}).keys())
