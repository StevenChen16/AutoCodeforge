#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Result Analyzer for AutoCodeforge.
This module processes and analyzes execution results.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

class ResultAnalyzer:
    """Analyzer for execution results."""
    
    def __init__(self):
        """Initialize the result analyzer."""
        logger.info("ResultAnalyzer initialized")
    
    def analyze(self, result: str) -> Dict[str, Any]:
        """
        Analyze execution results.
        
        Args:
            result: The execution result string
            
        Returns:
            Dictionary with analysis results
        """
        if not result:
            return {"success": False, "reason": "Empty result", "terminate": False}
        
        # Check for errors
        has_error = self._check_for_errors(result)
        
        # Check for success patterns
        success_patterns = self._identify_success_patterns(result)
        
        # Calculate overall success
        success = not has_error and len(success_patterns) > 0
        
        # Determine if we should terminate the cycle
        terminate = self._should_terminate(result, success)
        
        analysis = {
            "success": success,
            "has_error": has_error,
            "success_patterns": success_patterns,
            "terminate": terminate,
            "reason": self._determine_reason(result, success, terminate),
            "summary": self._summarize_result(result)
        }
        
        logger.info(f"Analysis completed: success={success}, terminate={terminate}")
        return analysis
    
    def _check_for_errors(self, result: str) -> bool:
        """Check if the result contains errors."""
        error_patterns = [
            r"ERROR:",
            r"Error:",
            r"Exception:",
            r"failed with exit code",
            r"Command failed",
            r"Traceback \(most recent call last\)",
            r"ModuleNotFoundError:",
            r"ImportError:",
            r"SyntaxError:",
            r"NameError:",
            r"TypeError:",
            r"ValueError:"
        ]
        
        for pattern in error_patterns:
            if re.search(pattern, result):
                return True
        
        return False
    
    def _identify_success_patterns(self, result: str) -> List[str]:
        """Identify success patterns in the result."""
        success_patterns = []
        
        # Check for basic success indicators
        if "successfully" in result.lower():
            success_patterns.append("success_keyword")
        
        # Check for test success
        if re.search(r"All tests passed|Tests passed|Test successful", result, re.IGNORECASE):
            success_patterns.append("test_success")
        
        # Check for build success
        if re.search(r"Build successful|Built successfully", result, re.IGNORECASE):
            success_patterns.append("build_success")
        
        # Check for server started
        if re.search(r"Server started|Running on|Listening on", result, re.IGNORECASE):
            success_patterns.append("server_started")
        
        return success_patterns
    
    def _should_terminate(self, result: str, success: bool) -> bool:
        """Determine if the cycle should terminate."""
        # Terminate on catastrophic errors
        if "CRITICAL ERROR" in result:
            return True
        
        # Look for explicit termination signals
        if re.search(r"Optimization complete|Goal achieved|Success criteria met", result, re.IGNORECASE):
            return True
        
        # Continue by default
        return False
    
    def _determine_reason(self, result: str, success: bool, terminate: bool) -> str:
        """Determine the reason for the current state."""
        if terminate:
            if "CRITICAL ERROR" in result:
                return "Critical error occurred"
            elif success:
                return "Success criteria met"
            else:
                return "Termination condition detected"
        
        if not success:
            for error_pattern in [
                (r"ModuleNotFoundError: No module named '([^']+)'", "Missing module: {}"),
                (r"ImportError: ([^\\n]+)", "Import error: {}"),
                (r"SyntaxError: ([^\\n]+)", "Syntax error: {}"),
                (r"TypeError: ([^\\n]+)", "Type error: {}"),
                (r"ValueError: ([^\\n]+)", "Value error: {}")
            ]:
                match = re.search(error_pattern[0], result)
                if match:
                    return error_pattern[1].format(match.group(1))
            
            return "Execution failed with errors"
        
        return "Execution completed successfully"
    
    def _summarize_result(self, result: str) -> str:
        """Create a short summary of the result."""
        # Extract the most relevant lines (first few and any error lines)
        lines = result.strip().split("\n")
        relevant_lines = []
        
        # Add first few lines
        for i in range(min(5, len(lines))):
            relevant_lines.append(lines[i])
        
        # Add lines with errors
        for line in lines[5:]:
            if any(error_word in line for error_word in ["error", "exception", "failed", "traceback"]):
                relevant_lines.append(line)
                
        # Limit the total number of lines
        if len(relevant_lines) > 10:
            relevant_lines = relevant_lines[:10]
            relevant_lines.append("...")
        
        return "\n".join(relevant_lines)
