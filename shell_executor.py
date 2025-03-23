#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Shell Executor for AutoCodeforge.
This module handles execution of commands in PowerShell.
"""

import os
import sys
import subprocess
import logging
import shlex
from typing import List, Optional, Dict, Any, Union

logger = logging.getLogger(__name__)

class PowerShellExecutor:
    """Executor for PowerShell commands."""
    
    def __init__(self, working_directory: Optional[str] = None):
        """
        Initialize the PowerShell executor.
        
        Args:
            working_directory: Working directory for command execution
        """
        self.working_directory = working_directory
        
        # Validate and create working directory if needed
        if working_directory:
            try:
                # First, check if directory exists
                if not os.path.exists(working_directory):
                    logger.info(f"Creating working directory: {working_directory}")
                    os.makedirs(working_directory, exist_ok=True)
                    
                # Log confirmation that directory exists
                if os.path.exists(working_directory):
                    logger.info(f"Working directory exists: {working_directory}")
                else:
                    logger.warning(f"Failed to create working directory: {working_directory}")
            except Exception as e:
                logger.error(f"Error setting up working directory {working_directory}: {e}")
                
        logger.info(f"PowerShellExecutor initialized with working directory: {working_directory or 'current'}")
        
        # Test PowerShell execution
        try:
            test_result = self._test_powershell()
            logger.info(f"PowerShell test: {test_result}")
        except Exception as e:
            logger.error(f"Error testing PowerShell: {e}")
    
    def _test_powershell(self) -> str:
        """Test basic PowerShell functionality."""
        try:
            # Simple test command
            cmd = "Write-Output 'PowerShell test successful'"
            
            # Execute directly using subprocess for testing
            process = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate(timeout=10)
            
            if process.returncode != 0:
                return f"PowerShell test failed with code {process.returncode}: {stderr}"
            
            return "PowerShell basic test successful"
        except Exception as e:
            return f"PowerShell test error: {e}"
    
    def set_working_directory(self, directory: str) -> None:
        """
        Set the working directory for command execution.
        
        Args:
            directory: Directory path to use for command execution
        """
        if os.path.exists(directory) and os.path.isdir(directory):
            self.working_directory = directory
            logger.info(f"Working directory set to: {directory}")
        else:
            logger.warning(f"Invalid working directory: {directory}. Creating it.")
            try:
                os.makedirs(directory, exist_ok=True)
                self.working_directory = directory
            except Exception as e:
                logger.error(f"Failed to create working directory {directory}: {e}")
                raise
    
    def execute(self, command: str, timeout: int = 300) -> str:
        """
        Execute a PowerShell command.
        
        Args:
            command: The PowerShell command to execute
            timeout: Timeout in seconds (default: 300)
            
        Returns:
            Command output as a string
        """
        # Verify working directory
        if self.working_directory:
            if not os.path.exists(self.working_directory):
                logger.info(f"Creating working directory before command execution: {self.working_directory}")
                os.makedirs(self.working_directory, exist_ok=True)
            
            # Check if directory actually exists now
            if not os.path.exists(self.working_directory):
                logger.error(f"Working directory still does not exist: {self.working_directory}")
                return f"ERROR: Working directory does not exist: {self.working_directory}"
        
        # Log the execution environment
        actual_working_dir = self.working_directory or os.getcwd()
        logger.info(f"Executing command in directory: {actual_working_dir}")
        logger.info(f"Command to execute: {command}")
        
        # Prepare PowerShell command to ensure working in correct directory
        # Properly escape paths with spaces and special characters
        escaped_working_dir = self.working_directory.replace("'", "''") if self.working_directory else ""
        
        if self.working_directory:
            # Method 1: Use Set-Location in PowerShell
            ps_command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", 
                          f"Set-Location -Path '{escaped_working_dir}'; {command}"]
            
            # Log the full command being executed 
            logger.info(f"Full PowerShell command: {' '.join(ps_command)}")
        else:
            ps_command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
            logger.info(f"Full PowerShell command (no working dir): {' '.join(ps_command)}")
        
        try:
            # Execute the command using list form for better argument handling
            process = subprocess.Popen(
                ps_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                # Still set working_directory for subprocess as a fallback
                cwd=self.working_directory,
                universal_newlines=True
            )
            
            # Wait for the process to complete with timeout
            stdout, stderr = process.communicate(timeout=timeout)
            
            # Check for errors
            if process.returncode != 0:
                error_message = f"PowerShell command failed with exit code {process.returncode}: {stderr}"
                logger.error(error_message)
                # Log the full error output
                if stderr:
                    logger.error(f"Command stderr: {stderr}")
                if stdout:
                    logger.error(f"Command stdout despite error: {stdout[:1000]}")
                return f"ERROR: {error_message}\n{stdout}"
            
            # Log the successful result with actual output
            log_output = stdout[:1000] + "..." if len(stdout) > 1000 else stdout
            logger.info(f"Command completed successfully with {len(stdout)} bytes of output")
            logger.info(f"Command output: {log_output}")
            return stdout
        
        except subprocess.TimeoutExpired:
            process.kill()
            error_message = f"Command timed out after {timeout} seconds"
            logger.error(error_message)
            return f"ERROR: {error_message}"
        
        except Exception as e:
            error_message = f"Error executing PowerShell command: {e}"
            logger.error(error_message)
            return f"ERROR: {error_message}"
    
    def execute_multiple(self, commands: List[str], stop_on_error: bool = False) -> List[Dict[str, str]]:
        """
        Execute multiple PowerShell commands.
        
        Args:
            commands: List of PowerShell commands to execute
            stop_on_error: Whether to stop execution on first error
            
        Returns:
            List of dictionaries containing command and output
        """
        results = []
        
        for cmd in commands:
            output = self.execute(cmd)
            results.append({
                "command": cmd,
                "output": output,
                "success": not output.startswith("ERROR:")
            })
            
            if stop_on_error and output.startswith("ERROR:"):
                logger.warning(f"Stopping command execution due to error in command: {cmd}")
                break
        
        return results
    
    def execute_script(self, script_content: str, script_args: Optional[List[str]] = None) -> str:
        """
        Execute a PowerShell script by creating a temporary script file.
        
        Args:
            script_content: The content of the PowerShell script
            script_args: Optional arguments to pass to the script
            
        Returns:
            Script output as a string
        """
        # Create a temporary script file - preferably in the working directory
        if self.working_directory and os.path.exists(self.working_directory):
            temp_dir = self.working_directory
        else:
            temp_dir = os.path.join(os.environ.get('TEMP', '.'), 'autocodforge')
            os.makedirs(temp_dir, exist_ok=True)
        
        script_path = os.path.join(temp_dir, f"script_{os.urandom(4).hex()}.ps1")
        logger.info(f"Creating temporary script at: {script_path}")
        
        try:
            # Write script content to file
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # Prepare command
            args_str = " ".join(script_args) if script_args else ""
            
            # Use relative path if script is in working directory
            if self.working_directory and script_path.startswith(self.working_directory):
                # Get relative path
                rel_path = os.path.basename(script_path)
                command = f". '.\\{rel_path}' {args_str}"
            else:
                # Use absolute path with proper escaping - fix syntax error
                escaped_path = script_path.replace("'", "''")
                command = f". '{escaped_path}' {args_str}"
            
            logger.info(f"Executing script with command: {command}")
            
            # Execute the script
            result = self.execute(command)
            
            return result
        
        finally:
            # Clean up the temporary script file
            try:
                if os.path.exists(script_path):
                    os.remove(script_path)
                    logger.info(f"Deleted temporary script: {script_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary script file {script_path}: {e}")
                
    def get_environment_info(self) -> Dict[str, Any]:
        """
        Get information about the execution environment.
        
        Returns:
            Dictionary with environment information
        """
        try:
            # Check working directory exists
            if self.working_directory and not os.path.exists(self.working_directory):
                logger.warning(f"Working directory does not exist: {self.working_directory}")
                os.makedirs(self.working_directory, exist_ok=True)
                
            # Get current directory in PowerShell
            logger.info("Getting current directory from PowerShell")
            current_dir_cmd = "Write-Output (Get-Location).Path"
            current_dir = self.execute(current_dir_cmd).strip()
            
            # Check if current_dir actually points to our working directory
            if self.working_directory:
                if not current_dir.startswith("ERROR:") and current_dir != self.working_directory:
                    logger.warning(f"Working directory mismatch: expected {self.working_directory}, got {current_dir}")
            
            # Get Python version
            logger.info("Checking Python version")
            python_version_cmd = "Write-Output (python --version)"
            python_version = self.execute(python_version_cmd).strip()
            
            # Get PowerShell version
            logger.info("Checking PowerShell version")
            ps_version_cmd = "Write-Output $PSVersionTable.PSVersion.ToString()"
            ps_version = self.execute(ps_version_cmd).strip()
            
            return {
                "python_version": python_version,
                "powershell_version": ps_version,
                "configured_working_directory": self.working_directory,
                "actual_working_directory": current_dir
            }
        except Exception as e:
            logger.error(f"Error getting environment info: {e}")
            return {"error": str(e)}
        
    def navigate_to_project(self) -> str:
        """
        Navigate to the project directory and verify it works.
        Returns current directory path after navigation.
        """
        if not self.working_directory:
            logger.warning("No working directory configured")
            return "No working directory configured"
        
        # Ensure directory exists
        if not os.path.exists(self.working_directory):
            logger.info(f"Creating working directory: {self.working_directory}")
            try:
                os.makedirs(self.working_directory, exist_ok=True)
            except Exception as e:
                logger.error(f"Error creating working directory: {e}")
                return f"Error creating directory: {e}"
                
        # Log the directory confirmation
        logger.info(f"Checking if working directory exists: {os.path.exists(self.working_directory)}")
            
        try:
            # Try to navigate to the directory and return the current path
            logger.info(f"Attempting to navigate to: {self.working_directory}")
            
            # Execute PowerShell Get-Location and capture current directory
            current_dir_cmd = "Write-Output (Get-Location).Path"
            current_dir = self.execute(current_dir_cmd).strip()
            
            # Check if successfully navigated
            if current_dir.startswith("ERROR:"):
                logger.error(f"Failed to get current directory: {current_dir}")
                return current_dir
                
            if current_dir != self.working_directory:
                logger.warning(f"Working directory mismatch: expected {self.working_directory}, got {current_dir}")
                
            # List directory contents to verify access
            dir_contents_cmd = "Get-ChildItem -Name"
            dir_contents = self.execute(dir_contents_cmd)
            
            if dir_contents.startswith("ERROR:"):
                logger.error(f"Failed to list directory contents: {dir_contents}")
            else:
                logger.info(f"Directory contents retrieved: {len(dir_contents.splitlines())} items")
                logger.info(f"Directory contents: {dir_contents}")
            
            return f"Current directory: {current_dir}\nContents:\n{dir_contents}"
        except Exception as e:
            logger.error(f"Error navigating to project directory: {e}")
            return f"Error: {str(e)}"
