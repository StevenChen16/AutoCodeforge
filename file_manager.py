#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File Manager for AutoCodeforge.
This module handles file system operations.
"""

import os
import logging
import shutil
from typing import List, Optional, Dict, Any, Union

logger = logging.getLogger(__name__)

class FileManager:
    """Manager for file system operations."""
    
    def __init__(self, base_path: str, project_name: Optional[str] = None):
        """
        Initialize the file manager.
        
        Args:
            base_path: Base directory for all file operations
            project_name: Optional project name for project-specific operations
        """
        self.base_path = os.path.abspath(base_path)
        self.project_name = project_name
        
        # Create base directory if it doesn't exist
        os.makedirs(self.base_path, exist_ok=True)
        
        # If project name is provided, use project-specific directory
        if project_name:
            self.project_path = os.path.join(self.base_path, self._sanitize_project_name(project_name))
            os.makedirs(self.project_path, exist_ok=True)
            logger.info(f"FileManager initialized with project path: {self.project_path}")
        else:
            self.project_path = self.base_path
            logger.info(f"FileManager initialized with base path: {self.base_path}")
    
    def _sanitize_project_name(self, project_name: str) -> str:
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
    
    def get_full_path(self, relative_path: str) -> str:
        """
        Get the full path from a path relative to the project directory.
        
        Args:
            relative_path: Path relative to the project directory
            
        Returns:
            Full absolute path
        """
        # Use project path as the base if available
        base_dir = self.project_path if hasattr(self, 'project_path') else self.base_path
        full_path = os.path.join(base_dir, relative_path)
        
        # Security check to prevent directory traversal
        normalized_path = os.path.normpath(full_path)
        if not normalized_path.startswith(base_dir):
            raise ValueError(f"Path traversal detected: {relative_path}")
        
        return full_path
    
    def read_file(self, relative_path: str) -> str:
        """
        Read the contents of a file.
        
        Args:
            relative_path: Path to the file, relative to project directory
            
        Returns:
            Contents of the file as a string
        """
        full_path = self.get_full_path(relative_path)
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Read file: {relative_path}")
            return content
        except Exception as e:
            logger.error(f"Error reading file {relative_path}: {e}")
            raise
    
    def write_file(self, relative_path: str, content: str) -> None:
        """
        Write content to a file, creating directories as needed.
        
        Args:
            relative_path: Path to the file, relative to project directory
            content: Content to write to the file
        """
        full_path = self.get_full_path(relative_path)
        
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Wrote file: {relative_path}")
        except Exception as e:
            logger.error(f"Error writing file {relative_path}: {e}")
            raise
    
    def delete_file(self, relative_path: str) -> None:
        """
        Delete a file.
        
        Args:
            relative_path: Path to the file, relative to project directory
        """
        full_path = self.get_full_path(relative_path)
        
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"Deleted file: {relative_path}")
            else:
                logger.warning(f"Attempted to delete non-existent file: {relative_path}")
        except Exception as e:
            logger.error(f"Error deleting file {relative_path}: {e}")
            raise
    
    def list_files(self, subdirectory: str = "") -> List[str]:
        """
        List all files in the project directory or a subdirectory.
        
        Args:
            subdirectory: Optional subdirectory to list files from
            
        Returns:
            List of relative file paths
        """
        dir_path = self.get_full_path(subdirectory)
        
        file_list = []
        try:
            for root, _, files in os.walk(dir_path):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, self.project_path)
                    file_list.append(rel_path)
            
            logger.info(f"Listed {len(file_list)} files in {subdirectory or 'project directory'}")
            return file_list
        except Exception as e:
            logger.error(f"Error listing files in {subdirectory or 'project directory'}: {e}")
            raise
    
    def read_file_content(self, relative_path: str) -> Dict[str, Any]:
        """
        Read a file and return its metadata along with content.
        
        Args:
            relative_path: Path to the file, relative to project directory
            
        Returns:
            Dict with file metadata and content
        """
        full_path = self.get_full_path(relative_path)
        
        try:
            content = self.read_file(relative_path)
            stat = os.stat(full_path)
            
            return {
                "path": relative_path,
                "full_path": full_path,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "content": content
            }
        except Exception as e:
            logger.error(f"Error getting file content for {relative_path}: {e}")
            raise
    
    def create_directory(self, relative_path: str) -> None:
        """
        Create a directory.
        
        Args:
            relative_path: Path to the directory, relative to project directory
        """
        full_path = self.get_full_path(relative_path)
        
        try:
            os.makedirs(full_path, exist_ok=True)
            logger.info(f"Created directory: {relative_path}")
        except Exception as e:
            logger.error(f"Error creating directory {relative_path}: {e}")
            raise
            
    def get_directory_structure(self) -> Dict[str, Any]:
        """
        Get a nested directory structure representation.
        
        Returns:
            Dictionary representing the directory structure
        """
        def _get_structure(path):
            result = {}
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    result[item] = _get_structure(item_path)
                else:
                    # For files, store size and modification time
                    stat = os.stat(item_path)
                    result[item] = {
                        "type": "file",
                        "size": stat.st_size,
                        "modified": stat.st_mtime
                    }
            return result
        
        try:
            structure = _get_structure(self.project_path)
            return structure
        except Exception as e:
            logger.error(f"Error getting directory structure: {e}")
            return {}
    
    def get_project_info(self) -> Dict[str, Any]:
        """
        Get information about the current project.
        
        Returns:
            Dictionary with project information
        """
        return {
            "name": self.project_name,
            "path": self.project_path,
            "file_count": len(self.list_files()),
            "structure": self.get_directory_structure()
        }
