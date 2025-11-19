
import os

try:
    os.environ["QWEN_BASE_URL"]
    os.environ["QWEN_API_KEY"]
except KeyError:
    import importlib

    dotenv = importlib.import_module("dotenv")
    dotenv.load_dotenv()

from xlangguage_nodes.requirement_agent.requirement_agent import (
    requirement_doc_prompt,
    requirement_doc_description,
    requirement_code_prompt,
    requirement_code_description,
)
from xlangguage_nodes.architecture_agent.architecture_agent import (
    architecture_agent_prompt,
    architecture_agent_description,
)
from xlangguage_nodes.system_agent.system_agent import (
    system_agent_prompt,
    system_agent_description,
)

from xlangguage_nodes.tool.cnki_search import cnki_search


xlangguage_agent_subagents = [
    {
        "name": "requirement_doc_agent",
        "description": requirement_doc_description,
        "prompt": requirement_doc_prompt,
        "tools": [
            "cnki_search",
            "read_file_content_and_history",
            "write_file",
            "edit_file_with_commit_message",
            "ls",
        ],
        "model_settings": {
            "model_provider": "openai",
            "model": "qwen-max",
            "temperature": 0,
            "base_url": os.environ["QWEN_BASE_URL"],
            "api_key": os.environ["QWEN_API_KEY"],
        },
        "read_permissions": ["requirement"],
        "write_permissions": ["requirement"],
    },
    {
        "name": "requirement_code_agent",
        "description": requirement_code_description,
        "prompt": requirement_code_prompt,
        "tools": [
            "read_file_content_and_history",
            "write_file",
            "edit_file_with_commit_message",
            "ls",
        ],
        "model_settings": {
            "model_provider": "openai",
            "model": "qwen-max",
            "temperature": 0,
            "base_url": os.environ["QWEN_BASE_URL"],
            "api_key": os.environ["QWEN_API_KEY"],
        },
        "read_permissions": ["requirement"],
        "write_permissions": ["requirement"],
    },
    {
        "name": "architecture_agent",
        "description": architecture_agent_description,
        "prompt": architecture_agent_prompt,
        "tools": [
            "read_file_content_and_history",
            "write_file",
            "edit_file_with_commit_message",
            "ls",
        ],
        "model_settings": {
            "model_provider": "openai",
            "model": "qwen-max",
            "temperature": 0,
            "base_url": os.environ["QWEN_BASE_URL"],
            "api_key": os.environ["QWEN_API_KEY"],
        },
        "read_permissions": ["requirement", "architecture"],
        "write_permissions": ["architecture"],
    },
    {
        "name": "system_agent",
        "description": system_agent_description,
        "prompt": system_agent_prompt,
        "tools": [
            "read_file_content_and_history",
            "write_file",
            "edit_file_with_commit_message",
            "ls",
        ],
        "model_settings": {
            "model_provider": "openai",
            "model": "qwen-max",
            "temperature": 0,
            "base_url": os.environ["QWEN_BASE_URL"],
            "api_key": os.environ["QWEN_API_KEY"],
        },
        "read_permissions": ["architecture", "system"],
        "write_permissions": ["system"],
    },
]

xlangguage_agent_model_settings = {
    "model": "qwen-max",
    "model_provider": "openai",
    "temperature": 0.1,
    "base_url": os.environ["QWEN_BASE_URL"],
    "api_key": os.environ["QWEN_API_KEY"],
}

# xlangguage_agent_model_settings = {
#     "model": "gemini-2.5-flash",
#     "model_provider": "openai",
#     "temperature": 0.1,
#     "base_url": os.environ["GOOGLE_API_BASE_URL"],
#     "api_key": os.environ["GOOGLE_API_KEY"],
# }

subagent_tools = [cnki_search]

