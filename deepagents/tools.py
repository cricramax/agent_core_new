from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from typing import Annotated
from langgraph.prebuilt import InjectedState

from deepagents.prompts import (
    WRITE_TODOS_DESCRIPTION,
    EDIT_DESCRIPTION,
    TOOL_DESCRIPTION,
    TOOL_DESCRIPTION_AND_HISTORY,
    EDIT_WITH_COMMIT_MESSAGE_DESCRIPTION,
)
from deepagents.state import Todo, DeepAgentState


@tool(description=WRITE_TODOS_DESCRIPTION)
def write_todos(
    todos: list[Todo], tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    return Command(
        update={
            "todos": todos,
            "messages": [
                ToolMessage(f"Updated todo list to {todos}", tool_call_id=tool_call_id)
            ],
        }
    )


@tool
def ls(
    file_dir: str = "",
    state: Annotated[DeepAgentState, InjectedState] = None
    ) -> list[str]:
    """List files in the mock file system.
    We now only support listing files in the first level of the mock file system.
    
    Args:
        file_dir: Directory to list files from. Can be:
            - "": List all files
            - "root": List all files in the root directory
            - first level directory name, for example: "visual_files", "scripts_files", etc.
       
    Returns:
        List of file paths in the specified directory
    """
    files = state.get("files", {})
    
    if not files:
        return []
    
    # If no directory specified, return all file paths
    if not file_dir or file_dir == "":
        return list(files.keys())
    
    # Filter files by directory prefix
    matching_files = []
    for file_path in files.keys():
        # Check if file is in the specified directory
        if "/" in file_path:
            # For paths like "visual_files/image.png"
            path_dir = file_path.split("/")[0]
            if path_dir == file_dir:
                matching_files.append(file_path)
        else:
            # For root level files, only include if looking for root
            if file_dir == "root":
                matching_files.append(file_path)
    
    return matching_files


@tool(description=TOOL_DESCRIPTION)
def read_file_content(
    file_path: str,
    state: Annotated[DeepAgentState, InjectedState],
    offset: int = 0,
    limit: int = 2000,
) -> str:
    """Read file content."""
    # if file_dir not in state.get("files", {}):
    #     return f"Error: Directory '{file_dir}' not found"
    # else:
    #     # file_dir_content = state.get("files", {})[file_dir]
    #     # if file_path not in file_dir_content:
    #     #     return f"Error: File '{file_path}' not found in directory '{file_dir}'"
    #     # else:
    mock_filesystem = state.get("files", {})
    if file_path not in mock_filesystem:
        return f"Error: File '{file_path}' not found"

    # Get file content
    content = mock_filesystem[file_path][-1]

    # Handle empty file
    if not content or content.strip() == "":
        return "System reminder: File exists but has empty contents"

    # Split content into lines
    lines = content.splitlines()

    # Apply line offset and limit
    start_idx = offset
    end_idx = min(start_idx + limit, len(lines))

    # Handle case where offset is beyond file length
    if start_idx >= len(lines):
        return f"Error: Line offset {offset} exceeds file length ({len(lines)} lines)"

    # Format output with line numbers (cat -n format)
    result_lines = []
    for i in range(start_idx, end_idx):
        line_content = lines[i]

        # Truncate lines longer than 2000 characters
        if len(line_content) > 2000:
            line_content = line_content[:2000]

        # Line numbers start at 1, so add 1 to the index
        line_number = i + 1
        result_lines.append(f"{line_number:6d}\t{line_content}")

    return "\n".join(result_lines)

@tool(description=TOOL_DESCRIPTION_AND_HISTORY)
def read_file_content_and_history(
    file_path: str,
    state: Annotated[DeepAgentState, InjectedState],
    offset: int = 0,
    limit: int = 2000,
) -> str:
    """Read file content and its edit history."""
    # if file_dir not in state.get("files", {}):
    #     return f"Error: Directory '{file_dir}' not found"
    # else:
    #     # file_dir_content = state.get("files", {})[file_dir]
    #     # if file_path not in file_dir_content:
    #     #     return f"Error: File '{file_path}' not found in directory '{file_dir}'"
    #     # else:
    mock_filesystem = state.get("files", {})
    if file_path not in mock_filesystem:
        return f"Error: File '{file_path}' not found"

    # Get file content
    content = "\n".join(mock_filesystem[file_path]) # list of strings

    # Handle empty file
    if not content or content.strip() == "":
        return "System reminder: File exists but has empty contents"

    # Split content into lines
    lines = content.splitlines()

    # Apply line offset and limit
    start_idx = offset
    end_idx = min(start_idx + limit, len(lines))

    # Handle case where offset is beyond file length
    if start_idx >= len(lines):
        return f"Error: Line offset {offset} exceeds file length ({len(lines)} lines)"

    # Format output with line numbers (cat -n format)
    result_lines = []
    for i in range(start_idx, end_idx):
        line_content = lines[i]

        # Truncate lines longer than 2000 characters
        if len(line_content) > 2000:
            line_content = line_content[:2000]

        # Line numbers start at 1, so add 1 to the index
        line_number = i + 1
        result_lines.append(f"{line_number:6d}\t{line_content}")

    return "\n".join(result_lines)


def write_file(
    file_path: str,
    content: str,
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Write to a new file."""
    files = state.get("files", {})
    files[file_path] = [content]
    return Command(
        update={
            "files": files,
            "messages": [
                ToolMessage(f"Updated file {file_path}", tool_call_id=tool_call_id)
            ],
        }
    )


@tool(description=EDIT_DESCRIPTION)
def edit_file(
    file_path: str,
    old_string: str,
    new_string: str,
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    replace_all: bool = False,
) -> Command:
    """Write to a file."""
    mock_filesystem = state.get("files", {})
    # Check if file exists in mock filesystem
    if file_path not in mock_filesystem:
        return f"Error: File '{file_path}' not found"

    # Get current file content
    content = mock_filesystem[file_path]

    # Check if old_string exists in the file
    if old_string not in content:
        return f"Error: String not found in file: '{old_string}'"

    # If not replace_all, check for uniqueness
    if not replace_all:
        occurrences = content.count(old_string)
        if occurrences > 1:
            return f"Error: String '{old_string}' appears {occurrences} times in file. Use replace_all=True to replace all instances, or provide a more specific string with surrounding context."
        elif occurrences == 0:
            return f"Error: String not found in file: '{old_string}'"

    # Perform the replacement
    if replace_all:
        new_content = content.replace(old_string, new_string)
        replacement_count = content.count(old_string)
        result_msg = f"Successfully replaced {replacement_count} instance(s) of the string in '{file_path}'"
    else:
        new_content = content.replace(
            old_string, new_string, 1
        )  # Replace only first occurrence
        result_msg = f"Successfully replaced string in '{file_path}'"

    # Update the mock filesystem
    mock_filesystem[file_path] = new_content
    return Command(
        update={
            "files": mock_filesystem,
            "messages": [ToolMessage(result_msg, tool_call_id=tool_call_id)],
        }
    )

@tool(description=EDIT_WITH_COMMIT_MESSAGE_DESCRIPTION)
def edit_file_with_commit_message(
    file_path: str,
    commit_message: str,
    new_content: str,
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    # replace_all: bool = False,
) -> Command:
    """Write to a file with a commit message."""
    mock_filesystem = state.get("files", {})
    # Check if file exists in mock filesystem
    if file_path not in mock_filesystem:
        return f"Error: File '{file_path}' not found"

    # Get current file content
    content = mock_filesystem[file_path]

    content.append(commit_message) # add commit message

    content.append(new_content) # add new content

    mock_filesystem[file_path] = content

    return Command(
        update={
            "files": mock_filesystem,
            "messages": [ToolMessage(f"Updated file {file_path} with commit message: {commit_message}", tool_call_id=tool_call_id)],
        }
    )
