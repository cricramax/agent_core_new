"""
DeepAgents - A general purpose 'deep agent' framework with sub-agent spawning, 
todo list capabilities, and mock file system. Built on LangGraph.
"""

__version__ = "0.0.4"

import os
import sys

# Add current directory to path for internal imports
sys.path.append(os.path.dirname(__file__))

# Core components
from deepagents.graph import create_deep_agent
from deepagents.state import DeepAgentState, Todo
from deepagents.sub_agent import SubAgent
from deepagents.model import get_default_model
from deepagents.interrupt import ToolInterruptConfig, create_interrupt_hook

# Built-in tools
from deepagents.tools import (
    write_todos,
    write_file, 
    read_file_content as read_file,
    edit_file,
    ls
)

# Public API exports
__all__ = [
    # Core functionality
    "create_deep_agent",
    "DeepAgentState", 
    "SubAgent",
    "Todo",
    
    # Configuration and utilities
    "get_default_model",
    "ToolInterruptConfig",
    "create_interrupt_hook",
    
    # Built-in tools
    "write_todos",
    "write_file",
    "read_file", 
    "edit_file",
    "ls",
    
    # Package info
    "__version__"
]
