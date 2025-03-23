#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AutoCodeforge: AI-powered automated code generation and optimization system.
This script contains the main entry point for the AutoCodeforge application.
"""

import os
import sys
import json
import time
import logging
import argparse
import traceback
from typing import Dict, List, Any, Optional, Union

# Local imports
from api_client import create_api_client, BaseAPIClient
from file_manager import FileManager
from shell_executor import PowerShellExecutor
from result_analyzer import ResultAnalyzer
from config import load_config, get_project_path, get_api_config, list_available_providers

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("autocodforge.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AutoCodeforge:
    """Main class for the AutoCodeforge application."""
    
    def __init__(self, project_name: str, config_path: str = "config.json", model_provider: Optional[str] = None):
        """
        Initialize the AutoCodeforge application.
        
        Args:
            project_name: Name of the project to work on
            config_path: Path to the configuration file
            model_provider: Optional model provider to use (claude, deepseek, etc.)
        """
        self.config = load_config(config_path)
        self.project_name = project_name
        
        # Set up project path
        self.project_path = get_project_path(self.config, project_name)
        logger.info(f"Project path: {self.project_path}")
        
        # Create project directory if it doesn't exist
        if not os.path.exists(self.project_path):
            logger.info(f"Creating project directory: {self.project_path}")
            os.makedirs(self.project_path, exist_ok=True)
        
        # Initialize components
        self.model_provider = model_provider or self.config["api"]["default_provider"]
        self.api_config = get_api_config(self.config, self.model_provider)
        
        logger.info(f"Using model provider: {self.model_provider}")
        
        try:
            self.api_client = create_api_client(
                provider=self.model_provider,
                api_key=self.api_config.get("api_key"),
                model=self.api_config.get("model"),
                base_url=self.api_config.get("base_url")
            )
            
            model_info = self.api_client.get_model_info()
            logger.info(f"API client initialized: {model_info['provider']} - {model_info['model']}")
        except Exception as e:
            logger.error(f"Failed to initialize API client: {e}")
            logger.error(traceback.format_exc())
            
            # Fall back to mock client
            logger.info("Falling back to mock API client")
            self.model_provider = "mock"
            self.api_client = create_api_client(provider="mock")
        
        self.file_manager = FileManager(self.config["file_manager"]["base_path"], project_name)
        self.shell_executor = PowerShellExecutor(self.project_path)
        self.result_analyzer = ResultAnalyzer()
        
        logger.info(f"AutoCodeforge initialized for project: {project_name}")
        
        # Verify that the shell executor is properly set up
        self._verify_environment()
    
    def _verify_environment(self):
        """Verify the execution environment and working directory."""
        try:
            # Directly check if directory exists
            if os.path.exists(self.project_path):
                logger.info(f"Project directory exists: {self.project_path}")
            else:
                logger.warning(f"Project directory does not exist: {self.project_path}")
                # Try to create it
                os.makedirs(self.project_path, exist_ok=True)
                logger.info(f"Created project directory: {self.project_path}")
            
            # Check that we can navigate to the project directory
            nav_result = self.shell_executor.navigate_to_project()
            logger.info(f"Project directory navigation check: {nav_result}")
            
            # Get environment info
            env_info = self.shell_executor.get_environment_info()
            actual_dir = env_info.get('actual_working_directory', 'unknown')
            logger.info(f"Environment info: Working dir = {actual_dir}")
            
            # Test PowerShell command execution
            test_cmd = "Write-Output 'Test command from AutoCodeforge'"
            test_result = self.shell_executor.execute(test_cmd)
            logger.info(f"Test command result: {test_result}")
            
        except Exception as e:
            logger.warning(f"Environment verification warning: {e}")
            logger.warning(traceback.format_exc())
    
    def change_model_provider(self, provider: str) -> bool:
        """
        Change the model provider.
        
        Args:
            provider: The provider name (claude, deepseek, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        available_providers = list_available_providers(self.config)
        if provider not in available_providers:
            logger.error(f"Provider '{provider}' not available. Available providers: {', '.join(available_providers)}")
            return False
        
        try:
            # Get configuration for the new provider
            self.api_config = get_api_config(self.config, provider)
            
            # Create new API client
            self.api_client = create_api_client(
                provider=provider,
                api_key=self.api_config.get("api_key"),
                model=self.api_config.get("model"),
                base_url=self.api_config.get("base_url")
            )
            
            self.model_provider = provider
            model_info = self.api_client.get_model_info()
            logger.info(f"Changed to {model_info['provider']} model: {model_info['model']}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to change model provider to '{provider}': {e}")
            return False
    
    def run_cycle(self, topic: str, iterations: int = 5) -> None:
        """
        Run the complete AutoCodeforge cycle.
        
        Args:
            topic: The topic or problem to work on
            iterations: Maximum number of iterations to run
        """
        logger.info(f"Starting AutoCodeforge cycle for topic: {topic}")
        
        # Initial prompt to AI
        current_result = None
        for i in range(iterations):
            logger.info(f"Starting iteration {i+1}/{iterations}")
            
            # 1. Generate code with API
            response = self.generate_code(topic, current_result, i)
            
            # 2. Parse structured output
            actions = self.parse_response(response)
            
            # 3. Execute file modifications
            self.execute_file_actions(actions.get("file_actions", []))
            
            # 4. Execute shell commands
            result = self.execute_shell_actions(actions.get("shell_actions", []))
            current_result = result
            
            # 5. Analyze results
            analysis = self.result_analyzer.analyze(result)
            
            logger.info(f"Completed iteration {i+1}")
            print(f"\nIteration {i+1} completed.")
            print(f"Status: {'Success' if analysis.get('success', False) else 'Failed'}")
            print(f"Result summary: {analysis.get('reason', '')}")
            
            # Check if we should terminate early
            if analysis.get("terminate", False):
                logger.info(f"Early termination at iteration {i+1} due to: {analysis.get('reason', 'unknown')}")
                print(f"\nEarly termination: {analysis.get('reason', 'Goal achieved')}")
                break
        
        logger.info(f"AutoCodeforge cycle completed after {i+1} iterations")
        print(f"\nAutoCodeforge cycle completed after {i+1} iterations.")
        print(f"Project is available at: {self.project_path}")
    
    def generate_code(self, topic: str, current_result: Optional[str] = None, iteration: int = 0) -> Any:
        """Generate code using AI API."""
        context = {
            "topic": topic,
            "iteration": iteration,
            "current_result": current_result,
            "project_name": self.project_name,
            "project_path": self.project_path,
            "current_files": self.file_manager.list_files()
        }
        
        prompt = self.build_prompt(context)
        system_prompt = self.build_system_prompt(context)
        response = self.api_client.send_message(prompt, system_prompt)
        
        return response
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        """Build a prompt for AI API."""
        topic = context["topic"]
        iteration = context["iteration"]
        current_result = context.get("current_result")
        current_files = context.get("current_files", [])
        project_name = context.get("project_name", "")
        project_path = context.get("project_path", "")
        
        # Base prompt
        prompt = f"""
        I need you to help me with the following task: {topic}
        
        This is iteration {iteration} of the AutoCodeforge cycle for project: {project_name}.
        The project is located at: {project_path}
        
        """
        
        # Add current files info if available
        if current_files:
            prompt += "Current files in the project:\n"
            for file in current_files:
                prompt += f"- {file}\n"
            
            # Add content of key files (like README, main source files)
            try:
                key_files = []
                for file in current_files:
                    if file.lower() in ["readme.md", "main.py", "index.html", "app.js", "app.py"]:
                        key_files.append(file)
                    elif file.endswith(".py") and len(key_files) < 5:
                        key_files.append(file)
                
                if key_files:
                    prompt += "\nContent of key files:\n"
                    for file in key_files:
                        content = self.file_manager.read_file(file)
                        prompt += f"\n--- {file} ---\n```\n{content}\n```\n"
            except Exception as e:
                logger.warning(f"Error including key file contents: {e}")
        
        # Add execution result if available
        if current_result is not None:
            prompt += f"\nResults from previous iteration:\n```\n{current_result}\n```\n"
        
        # Instructions for structured output
        prompt += """
        Please respond with a structured JSON output containing the following:
        
        1. "explanation": Brief explanation of your approach and changes
        2. "file_actions": List of file actions, each containing:
           - "action": "create", "modify", or "delete"
           - "path": File path relative to project root
           - "content": Complete file content (for create/modify)
        3. "shell_actions": List of PowerShell commands to execute
        
        Example response format:
        {
            "explanation": "I'm creating a basic Flask API with error handling...",
            "file_actions": [
                {
                    "action": "create",
                    "path": "api.py",
                    "content": "import flask\\n..."
                },
                {
                    "action": "create",
                    "path": "test_api.py",
                    "content": "import unittest\\n..."
                }
            ],
            "shell_actions": [
                "pip install flask",
                "python test_api.py",
                "python api.py"
            ]
        }
        
        IMPORTANT REQUIREMENTS:
        
        1. ALWAYS create thorough test cases that validate your code works correctly 
        2. Include commands to run the tests as part of your shell_actions
        3. If creating an application or tool, include example usage and test data
        4. Test various edge cases and potential error conditions
        5. Provide shell commands that demonstrate the functionality with real examples
        
        For example, if you implement a calculator, include commands like:
           - "python calculator.py 1 + 2"
           - "python calculator.py 10 * 5"
           - "python calculator.py 'sqrt' 16"
        
        All commands will be executed in the project directory. Do NOT include absolute paths 
        or 'cd' commands to change directories. Use simple commands like 'python calculator.py' 
        not complex paths.
        
        If test data is needed for the application, please include the necessary file_actions 
        to create test data files.
        """
        
        return prompt
    
    def build_system_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build a system prompt for API.
        
        Args:
            context: Context information for the prompt
            
        Returns:
            System prompt string
        """
        project_name = context.get("project_name", "")
        project_path = context.get("project_path", "")
        iteration = context.get("iteration", 0)
        
        system_prompt = f"""
        You are AutoCodeforge, an AI system that helps generate and optimize code.
        
        Your task is to help implement a solution for the given topic, focusing on writing functional, well-structured code.
        
        Current project: {project_name}
        Project directory: {project_path}
        Current iteration: {iteration}
        
        Guidelines:
        1. Create a complete, working solution that meets the requirements
        2. Write clean, well-documented code with proper error handling
        3. Use appropriate design patterns and best practices
        4. Return your response as a structured JSON object as specified
        5. Prioritize creating working code over explanations
        6. Include all necessary dependencies and setup commands
        7. ALWAYS create thorough test cases and example usage to verify functionality
        8. Ensure all file paths are relative to the project root
        
        For test cases and demonstration:
        - Create comprehensive test cases that verify core functionality
        - Include test scripts that handle both normal and edge cases
        - Generate shell commands that demonstrate usage with sample inputs
        - Provide clear examples of how to use the application/code
        - Test potential error cases and verify error handling works correctly
        
        For shell commands:
        - All commands will be executed from the project directory ({project_path})
        - Do NOT include absolute paths in your commands
        - Do NOT use 'cd' commands to change directories
        - For example, use "python calculator.py" not "python D:/path/to/calculator.py"
        - Keep commands simple and focused on the task
        - For installing packages, use "pip install package_name"
        - Include commands to run both tests and usage examples
        
        For test data generation:
        - Create realistic sample data when needed for testing
        - Generate files like sample.json, test.csv, or example_input.txt as appropriate
        - Include shell commands to verify the data is properly loaded
        
        Your output must be a valid JSON object that follows the specified format.
        Each file_action must contain complete code for the file (not snippets or partial updates).
        """
        
        return system_prompt
    
    def parse_response(self, response: Any) -> Dict[str, Any]:
        """
        Parse the structured response from AI.
        
        The response format can vary by provider.
        """
        try:
            # Extract the response text
            response_text = ""
            
            # Handle different response structures
            if hasattr(response, 'content'):
                # Claude-style Message object with content attribute
                for content_block in response.content:
                    if hasattr(content_block, 'type') and content_block.type == 'text':
                        response_text += content_block.text
            elif isinstance(response, dict):
                # Dictionary with content key (standardized response)
                if "content" in response:
                    for content_block in response["content"]:
                        if content_block.get("type") == "text":
                            response_text += content_block.get("text", "")
                # DeepSeek-style content might be in a different format
                elif "_original" in response and hasattr(response["_original"], "choices"):
                    response_text = response["_original"].choices[0].message.content
            else:
                # Fallback - try to convert to string
                logger.warning("Unrecognized response format - attempting to extract text")
                response_text = str(response)
            
            logger.debug(f"Extracted response text: {response_text[:100]}...")
            
            # Look for JSON block in the response
            try:
                # Find JSON-like content (between curly braces)
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_text = response_text[start_idx:end_idx]
                    actions = json.loads(json_text)
                    logger.info("Successfully parsed structured output")
                    return actions
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from response: {e}")
        
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            
        logger.warning("Could not find valid JSON in response, returning empty actions")
        return {"file_actions": [], "shell_actions": []}
    
    def execute_file_actions(self, file_actions: List[Dict[str, Any]]) -> None:
        """Execute file creation/modification/deletion actions."""
        for action in file_actions:
            action_type = action.get("action", "")
            path = action.get("path", "")
            content = action.get("content", "")
            
            if not path:
                logger.warning(f"Skipping file action with empty path: {action}")
                continue
            
            try:
                if action_type == "create":
                    self.file_manager.write_file(path, content)
                    logger.info(f"Created file: {path}")
                    print(f"Created file: {path}")
                elif action_type == "modify":
                    self.file_manager.write_file(path, content)
                    logger.info(f"Modified file: {path}")
                    print(f"Modified file: {path}")
                elif action_type == "delete":
                    self.file_manager.delete_file(path)
                    logger.info(f"Deleted file: {path}")
                    print(f"Deleted file: {path}")
                else:
                    logger.warning(f"Unknown file action type: {action_type}")
                    print(f"Unknown file action: {action_type} for {path}")
            except Exception as e:
                logger.error(f"Failed to execute file action: {action_type} on {path}. Error: {e}")
                print(f"Error with file {path}: {e}")
    
    def execute_shell_actions(self, shell_actions: List[str]) -> str:
        """Execute PowerShell commands and return results."""
        all_results = []
        
        # First verify we're in the right directory
        check_cmd = "Write-Output (Get-Location).Path"
        check_dir = self.shell_executor.execute(check_cmd)
        logger.info(f"Working directory check before executing commands: {check_dir.strip()}")
        
        if check_dir.startswith("ERROR:"):
            logger.warning("Failed to determine current directory, execution may fail")
            
            # Try to verify directory exists
            if not os.path.exists(self.project_path):
                logger.error(f"Project directory doesn't exist: {self.project_path}")
                try:
                    os.makedirs(self.project_path, exist_ok=True)
                    logger.info(f"Created project directory: {self.project_path}")
                except Exception as create_err:
                    logger.error(f"Failed to create project directory: {create_err}")
        
        # Execute each command
        for cmd in shell_actions:
            try:
                print(f"Executing: {cmd}")
                logger.info(f"Executing shell command: {cmd}")
                
                # Execution
                result = self.shell_executor.execute(cmd)
                
                # Log result summary
                if result.startswith("ERROR:"):
                    logger.error(f"Command failed: {cmd}")
                    logger.error(f"Error details: {result[:200]}...")
                else:
                    result_preview = result.strip()[:100] + ("..." if len(result) > 100 else "")
                    logger.info(f"Command succeeded: {cmd}")
                    logger.info(f"Result preview: {result_preview}")
                
                all_results.append(f"Command: {cmd}\nResult:\n{result}\n")
                
                # Print command result to console
                print(f"Result: {result[:300]}{'...' if len(result) > 300 else ''}")
            except Exception as e:
                error_msg = f"Error executing command '{cmd}': {e}"
                all_results.append(f"Command: {cmd}\nError: {error_msg}\n")
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                print(f"Error: {error_msg}")
        
        return "\n".join(all_results)
    
    def interactive_session(self):
        """Run an interactive session for the user."""
        print(f"\nAutoCodeforge interactive session for project: {self.project_name}")
        print(f"Project path: {self.project_path}")
        print(f"AI model: {self.model_provider} - {self.api_config.get('model', 'default')}")
        print("Type 'help' for available commands, 'exit' to quit")
        
        while True:
            try:
                command = input("\nAutoCodeforge> ").strip()
                
                if command.lower() in ['exit', 'quit']:
                    print("Exiting AutoCodeforge...")
                    break
                    
                elif command.lower() == 'help':
                    self._print_help()
                    
                elif command.lower().startswith('run '):
                    # Run a PowerShell command
                    cmd = command[4:].strip()
                    print(f"Executing: {cmd}")
                    result = self.shell_executor.execute(cmd)
                    print(result)
                    
                elif command.lower() == 'list':
                    # List files in the project
                    files = self.file_manager.list_files()
                    print(f"Files in project ({len(files)}):")
                    for file in files:
                        print(f"- {file}")
                        
                elif command.lower().startswith('view '):
                    # View file content
                    path = command[5:].strip()
                    try:
                        content = self.file_manager.read_file(path)
                        print(f"\n--- {path} ---")
                        print(content)
                    except Exception as e:
                        print(f"Error reading file: {e}")
                        
                elif command.lower().startswith('edit '):
                    # Edit file (not implemented, just info)
                    path = command[5:].strip()
                    print(f"To edit {path}, use your preferred text editor to open:")
                    print(f"{os.path.join(self.project_path, path)}")
                    
                elif command.lower() == 'status':
                    # Show project status
                    files = self.file_manager.list_files()
                    print(f"Project: {self.project_name}")
                    print(f"Path: {self.project_path}")
                    print(f"Files: {len(files)}")
                    print(f"AI model: {self.model_provider} - {self.api_config.get('model', 'default')}")
                    
                    # Show current directory in PowerShell
                    current_dir = self.shell_executor.execute("Write-Output (Get-Location).Path").strip()
                    print(f"Current PowerShell directory: {current_dir}")
                    
                elif command.lower() == 'verify':
                    # Verify environment
                    print("Verifying environment...")
                    try:
                        self._verify_environment()
                        print("Environment verification complete. Check logs for details.")
                        
                        # Show current directory
                        check_cmd = "Write-Output (Get-Location).Path"
                        check_dir = self.shell_executor.execute(check_cmd).strip()
                        print(f"Current working directory: {check_dir}")
                        
                        # List directory
                        dir_cmd = "Get-ChildItem -Name"
                        dir_list = self.shell_executor.execute(dir_cmd)
                        print(f"Directory contents:\n{dir_list}")
                    except Exception as e:
                        print(f"Verification failed: {e}")
                    
                elif command.lower() == 'env':
                    # Show environment info
                    env_info = self.shell_executor.get_environment_info()
                    print("\nEnvironment Information:")
                    for key, value in env_info.items():
                        if isinstance(value, str) and len(value) > 100:
                            value = value[:100] + "..."
                        print(f"{key}: {value}")
                    
                elif command.lower() == 'test':
                    # Run tests
                    print("Running tests...")
                    test_files = [f for f in self.file_manager.list_files() if f.startswith('test_') and f.endswith('.py')]
                    
                    if not test_files:
                        print("No test files found. Test files should start with 'test_' and end with '.py'")
                    else:
                        for test_file in test_files:
                            print(f"Running test file: {test_file}")
                            result = self.shell_executor.execute(f"python {test_file}")
                            print(result)
                
                elif command.lower() == 'models':
                    # List available models
                    providers = list_available_providers(self.config)
                    print("\nAvailable AI models:")
                    for provider in providers:
                        provider_config = get_api_config(self.config, provider)
                        model = provider_config.get("model", "default")
                        active = " (active)" if provider == self.model_provider else ""
                        print(f"- {provider}: {model}{active}")
                    print("\nUse 'model <provider>' to switch models")
                
                elif command.lower().startswith('model '):
                    # Change model
                    provider = command[6:].strip().lower()
                    print(f"Switching to model provider: {provider}")
                    
                    if self.change_model_provider(provider):
                        print(f"Successfully switched to {provider} model: {self.api_config.get('model', 'default')}")
                    else:
                        print(f"Failed to switch to {provider}. See log for details.")
                    
                elif command.lower().startswith('forge '):
                    # Run a new forge cycle
                    topic = command[6:].strip()
                    iterations = 3  # Default number of iterations for interactive
                    print(f"Starting new forge cycle with topic: {topic}")
                    self.run_cycle(topic, iterations)
                    
                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for available commands")
                    
            except KeyboardInterrupt:
                print("\nOperation cancelled by user")
                
            except Exception as e:
                logger.error(f"Error in interactive session: {e}")
                logger.error(traceback.format_exc())
                print(f"Error: {e}")
    
    def _print_help(self):
        """Print help information."""
        print("\nAvailable commands:")
        print("  help                 - Show this help message")
        print("  list                 - List all files in the project")
        print("  view <file>          - View the content of a file")
        print("  edit <file>          - Show path to edit a file")
        print("  run <command>        - Run a PowerShell command")
        print("  test                 - Run available test files")
        print("  forge <topic>        - Start a new forge cycle")
        print("  models               - List available AI models")
        print("  model <provider>     - Switch to a different AI model")
        print("  status               - Show project status")
        print("  verify               - Verify environment setup")
        print("  env                  - Show environment information")
        print("  exit                 - Exit the interactive session")


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="AutoCodeforge: AI-powered automated code generation")
    parser.add_argument("topic", nargs="?", help="The topic or problem to work on")
    parser.add_argument("--project", "-p", type=str, help="Project name (defaults to sanitized topic)")
    parser.add_argument("--iterations", "-i", type=int, default=5, help="Maximum number of iterations")
    parser.add_argument("--interactive", "-int", action="store_true", help="Start interactive session after completion")
    parser.add_argument("--model", "-m", type=str, help="AI model to use (claude, deepseek, mock)")
    
    args = parser.parse_args()
    
    # Load config to get available providers
    config = load_config("config.json")
    available_providers = list_available_providers(config)
    
    # If no args are provided, show help and start interactive session
    if len(sys.argv) == 1:
        parser.print_help()
        
        # Ask for project name
        project_name = input("\nEnter project name: ")
        if not project_name:
            print("Project name is required.")
            sys.exit(1)
        
        # Ask for model provider
        print(f"\nAvailable AI models: {', '.join(available_providers)}")
        model_provider = input(f"Select AI model [{config['api']['default_provider']}]: ").strip().lower()
        if not model_provider:
            model_provider = config['api']['default_provider']
        
        if model_provider not in available_providers:
            print(f"Invalid model provider: {model_provider}. Using default.")
            model_provider = config['api']['default_provider']
            
        try:
            app = AutoCodeforge(project_name, model_provider=model_provider)
            app.interactive_session()
        except Exception as e:
            logger.error(f"Error running AutoCodeforge: {e}", exc_info=True)
            sys.exit(1)
        return
    
    # Regular execution with args
    topic = args.topic
    project_name = args.project or topic
    iterations = args.iterations
    model_provider = args.model
    
    # Validate model provider if specified
    if model_provider and model_provider not in available_providers:
        print(f"Invalid model provider: {model_provider}. Available providers: {', '.join(available_providers)}")
        sys.exit(1)
    
    try:
        app = AutoCodeforge(project_name, model_provider=model_provider)
        
        if topic:
            app.run_cycle(topic, iterations)
        
        # Always enter interactive mode if requested or after task completion
        if args.interactive or True:  # Always enter interactive mode
            app.interactive_session()
            
    except Exception as e:
        logger.error(f"Error running AutoCodeforge: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
