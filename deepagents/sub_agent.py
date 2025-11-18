from deepagents.prompts import TASK_DESCRIPTION_PREFIX, TASK_DESCRIPTION_SUFFIX
from deepagents.state import DeepAgentState
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import BaseTool
from typing_extensions import TypedDict
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage, HumanMessage
from langchain_core.language_models import LanguageModelLike
from langchain.chat_models import init_chat_model
from typing import Annotated, NotRequired, Any, Union, Sequence, Callable
from langgraph.types import Command
from deepagents.prompts import (
    SUB_AGENT_DESCRIPTION_SUFFIX,
    FILE_INSTRUCTION_SUFFIX,
)

from langgraph.prebuilt import InjectedState
from deepagents.utils import create_node_llm
from langgraph.config import get_stream_writer
import json
from langgraph.checkpoint.memory import InMemorySaver

class SubAgent(TypedDict):
    name: str
    description: str
    prompt: str
    tools: NotRequired[list[str]]
    # Optional per-subagent model: can be either a model instance OR dict settings
    model: NotRequired[Union[LanguageModelLike, dict[str, Any]]]
    write_permissions: NotRequired[list[str]]
    read_permissions: NotRequired[list[str]]


def _create_task_tool(
    tools, instructions, 
    subagents: list[SubAgent], 
    subagent_tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    model, state_schema,
    checkpointer=None
    ):
    agents = {
        "general-purpose": create_react_agent(model, prompt=instructions, tools=tools, checkpointer=False)
    }
    tools_by_name = {}
    all_tools = tools + subagent_tools # add subagent tools to the tools
    for tool_ in all_tools:
        if not isinstance(tool_, BaseTool):
            tool_ = tool(tool_)
        tools_by_name[tool_.name] = tool_
    for _agent in subagents:
        if "tools" in _agent:
            _tools = [tools_by_name[t] for t in _agent["tools"]]
            # print(_tools)
        else:
            _tools = tools
        # Resolve per-subagent model: can be instance or dict
        if "model" in _agent:
            agent_model = _agent["model"]
            if isinstance(agent_model, dict):
                # Dictionary settings - create model from config
                sub_model = create_node_llm(agent_model)
            else:
                # Model instance - use directly
                sub_model = agent_model
        else:
            # Fallback to main model
            sub_model = model
        _agent_prompt = _agent["prompt"] + SUB_AGENT_DESCRIPTION_SUFFIX + \
            FILE_INSTRUCTION_SUFFIX.format(read_permissions=_agent["read_permissions"], write_permissions=_agent["write_permissions"])
        if checkpointer is None:
            checkpointer = InMemorySaver()
        agents[_agent["name"]] = create_react_agent(
            sub_model, prompt=_agent_prompt, 
            tools=_tools, state_schema=state_schema, checkpointer=checkpointer
        )

    other_agents_string = [
        f"- {_agent['name']}: {_agent['description']}" for _agent in subagents
    ]

    @tool(
        description=TASK_DESCRIPTION_PREFIX.format(other_agents=other_agents_string)
        + TASK_DESCRIPTION_SUFFIX
    )
    async def task(
        description: str,
        subagent_type: str,
        state: Annotated[DeepAgentState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ):
        if subagent_type not in agents:
            return f"Error: invoked agent of type {subagent_type}, the only allowed types are {[f'`{k}`' for k in agents]}"
        sub_agent = agents[subagent_type]
        state["messages"] = [{"role": "user", "content": description}]
        # Emit structured custom events for streaming; main aggregates display
        # result = await sub_agent.ainvoke(state)
        writer = get_stream_writer()
        writer({
            "subagent": {"type": "start", "name": subagent_type, "description": description}
        })
        
        # # Create config for sub-agent
        # from langchain_core.runnables import RunnableConfig
        # sub_config = RunnableConfig({"configurable": {"thread_id": f"sub_agent_{subagent_type}_{tool_call_id}"}})
        
        # Create config for sub-agent
        from langchain_core.runnables import RunnableConfig
        sub_config = RunnableConfig({"configurable": {"thread_id": f"sub_agent_{subagent_type}_{tool_call_id}"}})

        # Forward sub-agent streaming as entire chunks; main will process uniformly
        async for chunk in sub_agent.astream(state, config=sub_config, stream_mode=["messages", "updates", "custom"]):
            stream_type, data = chunk
            writer({
                "subagent": {
                    "type": "chunk",
                    "name": subagent_type,
                    "stream_type": stream_type,
                    "data": data,
                }
            })
        # Get final state after streaming completes
        final_state = sub_agent.get_state(sub_config)
        result = final_state.values if hasattr(final_state, 'values') else {"messages": [{"role": "assistant", "content": "子智能体任务完成"}]}
        writer({"subagent": {"type": "stop"}})
        
        return Command(
            update={
                "files": result.get("files", {}),
                "messages": [
                    ToolMessage(
                        result["messages"][-1].content, tool_call_id=tool_call_id
                    )
                ],
            }
        )

    return task
