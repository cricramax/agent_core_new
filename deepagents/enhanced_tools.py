from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from typing import Annotated
from langgraph.prebuilt import InjectedState
from langgraph.config import get_stream_writer
from deepagents.state import Todo, DeepAgentState
from deepagents.prompts import (
    WRITE_TODOS_DESCRIPTION,
    EDIT_DESCRIPTION,
    TOOL_DESCRIPTION,
    EDIT_WITH_COMMIT_MESSAGE_DESCRIPTION,
)


@tool(description=WRITE_TODOS_DESCRIPTION)
def write_todos_with_streaming(
    todos: list[Todo], tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Enhanced write_todos with streaming support."""
    try:
        writer = get_stream_writer()
        writer({
            "type": "sub_agent_step",
            "step": "updating_todos",
            "message": f"Updating TODO list with {len(todos)} items",
            "data": {"todo_count": len(todos)}
        })
    except:
        # Fallback if streaming is not available
        pass
    
    return Command(
        update={
            "todos": todos,
            "messages": [
                ToolMessage(f"Updated todo list to {todos}", tool_call_id=tool_call_id)
            ],
        }
    )


def write_file_with_streaming(
    file_path: str,
    content: str,
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Enhanced write_file with streaming support."""
    try:
        writer = get_stream_writer()
        writer({
            "type": "sub_agent_step",
            "step": "writing_file",
            "message": f"Creating new file: {file_path}",
            "data": {
                "file_path": file_path,
                "content_length": len(content),
                "file_type": file_path.split('.')[-1] if '.' in file_path else 'unknown'
            }
        })
    except:
        # Fallback if streaming is not available
        pass
    
    files = state.get("files", {})
    files[file_path] = [content]
    
    try:
        writer = get_stream_writer()
        writer({
            "type": "sub_agent_step",
            "step": "file_written",
            "message": f"Successfully wrote {len(content)} characters to {file_path}",
            "data": {"file_path": file_path, "success": True}
        })
    except:
        pass
    
    return Command(
        update={
            "files": files,
            "messages": [
                ToolMessage(f"Updated file {file_path}", tool_call_id=tool_call_id)
            ],
        }
    )


@tool(description=EDIT_WITH_COMMIT_MESSAGE_DESCRIPTION)
def edit_file_with_commit_message_and_streaming(
    file_path: str,
    old_string: str,
    new_string: str,
    commit_message: str,
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    replace_all: bool = False,
) -> Command:
    """Enhanced edit_file with streaming and commit message support."""
    try:
        writer = get_stream_writer()
        writer({
            "type": "sub_agent_step",
            "step": "editing_file",
            "message": f"Editing file: {file_path}",
            "data": {
                "file_path": file_path,
                "commit_message": commit_message,
                "old_length": len(old_string),
                "new_length": len(new_string)
            }
        })
    except:
        pass
    
    mock_filesystem = state.get("files", {})
    
    # Check if file exists
    if file_path not in mock_filesystem:
        error_msg = f"Error: File '{file_path}' not found"
        try:
            writer = get_stream_writer()
            writer({
                "type": "sub_agent_step",
                "step": "file_edit_error",
                "message": error_msg,
                "data": {"file_path": file_path, "error": "file_not_found"}
            })
        except:
            pass
        return Command(
            update={
                "messages": [
                    ToolMessage(error_msg, tool_call_id=tool_call_id)
                ],
            }
        )

    # Get current file content (latest version)
    content = mock_filesystem[file_path][-1]

    # Check if old_string exists in the file
    if old_string not in content:
        error_msg = f"Error: String not found in file: '{old_string[:100]}...'"
        try:
            writer = get_stream_writer()
            writer({
                "type": "sub_agent_step",
                "step": "file_edit_error", 
                "message": error_msg,
                "data": {"file_path": file_path, "error": "string_not_found"}
            })
        except:
            pass
        return Command(
            update={
                "messages": [
                    ToolMessage(error_msg, tool_call_id=tool_call_id)
                ],
            }
        )

    # Check for uniqueness if not replace_all
    if not replace_all and content.count(old_string) > 1:
        error_msg = f"Error: String appears {content.count(old_string)} times in file. Use replace_all=True to replace all occurrences."
        try:
            writer = get_stream_writer()
            writer({
                "type": "sub_agent_step",
                "step": "file_edit_error",
                "message": error_msg,
                "data": {"file_path": file_path, "error": "multiple_matches", "count": content.count(old_string)}
            })
        except:
            pass
        return Command(
            update={
                "messages": [
                    ToolMessage(error_msg, tool_call_id=tool_call_id)
                ],
            }
        )

    # Perform replacement
    if replace_all:
        new_content = content.replace(old_string, new_string)
        replacements = content.count(old_string)
    else:
        new_content = content.replace(old_string, new_string, 1)
        replacements = 1

    # Update file history
    mock_filesystem[file_path].append(new_content)
    
    try:
        writer = get_stream_writer()
        writer({
            "type": "sub_agent_step",
            "step": "file_edited",
            "message": f"Successfully edited {file_path} - {replacements} replacement(s) made",
            "data": {
                "file_path": file_path,
                "commit_message": commit_message,
                "replacements": replacements,
                "content_length": len(new_content)
            }
        })
    except:
        pass

    return Command(
        update={
            "files": mock_filesystem,
            "messages": [
                ToolMessage(f"Updated file {file_path}. Commit: {commit_message}", tool_call_id=tool_call_id)
            ],
        }
    )


def read_file_with_streaming(
    file_path: str,
    state: Annotated[DeepAgentState, InjectedState],
    offset: int = 0,
    limit: int = 2000,
) -> str:
    """Enhanced read_file with streaming support."""
    try:
        writer = get_stream_writer()
        writer({
            "type": "sub_agent_step",
            "step": "reading_file",
            "message": f"Reading file: {file_path}",
            "data": {"file_path": file_path, "offset": offset, "limit": limit}
        })
    except:
        pass
    
    mock_filesystem = state.get("files", {})
    if file_path not in mock_filesystem:
        error_msg = f"Error: File '{file_path}' not found"
        try:
            writer = get_stream_writer()
            writer({
                "type": "sub_agent_step",
                "step": "file_read_error",
                "message": error_msg,
                "data": {"file_path": file_path, "error": "file_not_found"}
            })
        except:
            pass
        return error_msg

    # Get file content (latest version)
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

    # Format output with line numbers
    result_lines = []
    for i in range(start_idx, end_idx):
        line_content = lines[i]

        # Truncate lines longer than 2000 characters
        if len(line_content) > 2000:
            line_content = line_content[:2000]

        # Line numbers start at 1
        line_number = i + 1
        result_lines.append(f"{line_number:6d}\t{line_content}")

    try:
        writer = get_stream_writer()
        writer({
            "type": "sub_agent_step",
            "step": "file_read_complete",
            "message": f"Read {len(result_lines)} lines from {file_path}",
            "data": {
                "file_path": file_path,
                "lines_read": len(result_lines),
                "total_lines": len(lines)
            }
        })
    except:
        pass

    return "\n".join(result_lines) 