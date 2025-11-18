
try: 
    os.environ["QWEN_BASE_URL"]
    os.environ["QWEN_API_KEY"]
except:
    import os
    import dotenv

    dotenv.load_dotenv()

from xlangguage_nodes.requirement_agent.requirement_agent import (
    requirement_agent_prompt,
    requirement_agent_description,
)

from xlangguage_nodes.tool.cnki_search import cnki_search


xlangguage_agent_subagents = [
    {
        "name": "requirement_agent",
        "description": requirement_agent_description,
        "prompt": requirement_agent_prompt,
        "tools": ["cnki_search", \
            "read_file_content_and_history", \
            "write_file", "edit_file_with_commit_message", "ls"],
        "model_settings": {
            "model_provider": "openai",
            "model": "qwen-max",
            "temperature": 0,
            "base_url": os.environ["QWEN_BASE_URL"],
            "api_key": os.environ["QWEN_API_KEY"]
        },
        # "model_settings": {
        #     "model_provider": "openai",
        #     "model": "gemini-2.5-flash",
        #     "temperature": 0,
        #     "base_url": os.environ["GOOGLE_API_BASE_URL"],
        #     "api_key": os.environ["GOOGLE_API_KEY"]
        # },
        "read_permissions": ["requirement"],
        "write_permissions": ["requirement"],
    }
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

