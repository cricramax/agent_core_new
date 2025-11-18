from dotenv import load_dotenv
import os
import json
import json
load_dotenv()
from xlangguage_nodes.xlangguage_agent import xlangguage_agent
from langsmith import traceable
from langchain_core.runnables import RunnableConfig
from deepagents.stream_utils import UI_VISIBILITY, init_stream_state, process_stream_chunk

config = RunnableConfig({"configurable": {"thread_id": "1235678"}})
agent = xlangguage_agent


@traceable
async def main():
    while True:
        user_input = input("Enter a question: ")
        if user_input.lower() in ["exit", "quit", "bye"]:
            break

        main_state = init_stream_state()
        subagent_states = {}

        async for chunk in agent.astream(
            {"messages": user_input},
            config=config,
            stream_mode=["messages", "updates", "custom"],
        ):
            stream_type, data = chunk
            process_stream_chunk(
                stream_type=stream_type,
                data=data,
                main_state=main_state,
                subagent_states=subagent_states,
                ui=UI_VISIBILITY,
                print_fn=print,
            )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
