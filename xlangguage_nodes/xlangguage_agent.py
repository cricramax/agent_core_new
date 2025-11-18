xlangguage_agent_instruction = """

you are a helpful assistant that can help with xlangguage generating tasks.

you will receive a task to do system modeling.

you should use task to call different subagents to do the task.

you dont need to write any code, you just need to call the subagents to do the task.
"""

from xlangguage_nodes.agent_config import (
    xlangguage_agent_subagents,
    subagent_tools,
    xlangguage_agent_model_settings,
)
from deepagents import create_deep_agent
try:
    from langgraph.checkpoint.mongodb import MongoDBSaver
    from pymongo import MongoClient
    MONGODB_URI = "mongodb+srv://longxiao202110:200108LongXiao@cluster0.2sjxemh.mongodb.net/"

    mongodb_client = MongoClient(MONGODB_URI)
    checkpointer = MongoDBSaver(mongodb_client)
    print(f"Using MongoDB checkpointer: {checkpointer}")
except:
    # from langgraph.checkpoint.memory import InMemorySaver
    # checkpointer = InMemorySaver()
    # print(f"Using InMemorySaver: {checkpointer}")
    import aiosqlite
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    conn = aiosqlite.connect("memory.db")
    checkpointer = AsyncSqliteSaver(conn)
    print(f"Using SQLite checkpointer: {checkpointer}")

xlangguage_agent = create_deep_agent(
    tools=[],
    instructions=xlangguage_agent_instruction,
    model=xlangguage_agent_model_settings,
    subagents=xlangguage_agent_subagents,
    subagent_tools=subagent_tools,
    checkpointer=checkpointer,
)
