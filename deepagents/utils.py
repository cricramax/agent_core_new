# llm model config utils

from typing import Optional
# from state import VideoGenerationState
from pydantic import BaseModel

# ==============================================================================
# LLM config
# ==============================================================================

def create_node_llm(node_config: dict, tools: Optional[list] = [], structured_output_model: Optional[type[BaseModel]] = None):
    """
    为特定节点创建配置好的 LLM
    
    Args:
        base_llm: 基础可配置 LLM
        node_config: 节点特定配置
        tools: 节点特定工具列表
    
    Returns:
        配置好的 LLM 实例
    """
    from langchain.chat_models import init_chat_model

    print(f"node_config: {node_config}")
    configured_llm = init_chat_model(
        model=node_config.get("model", None),
        model_provider=node_config.get("model_provider", None),
        temperature=node_config.get("temperature", None),
        max_retries=node_config.get("max_retries", None),
        api_key=node_config.get("api_key", None),
        base_url=node_config.get("base_url", None)
    )
    # print(f"configured_llm: {configured_llm}")
    if tools:
        configured_llm = configured_llm.bind_tools(tools)
        # print(f"configured_llm_with_tools: {configured_llm}")
    if structured_output_model:
        # configured_llm = configured_llm.with_structured_output(create_gemini_compatible_schema(structured_output_model))
        fully_inlined_schema = create_fully_inlined_schema(structured_output_model) # gemini api 不支持 $ref 和 $defs
        configured_llm = configured_llm.with_structured_output(fully_inlined_schema)
        # print(f"configured_llm_with_structured_output: {configured_llm}")
    
    return configured_llm

def create_fully_inlined_schema(pydantic_model: type[BaseModel]) -> dict:
    """
    Generates a Pydantic schema and fully inlines all references to make it
    compatible with APIs that do not support '$ref' or 'definitions'.
    """
    # Generate the initial schema with '$defs'
    schema = pydantic_model.model_json_schema()

    if "$defs" not in schema:
        # If there are no definitions, the schema is already simple enough.
        return schema

    # Get the definitions that we will be inlining
    defs = schema.pop("$defs")

    # This is our recursive function to resolve references
    def resolve_refs(node):
        if isinstance(node, dict):
            if "$ref" in node:
                # Resolve the reference
                ref_path = node["$ref"]
                # Assumes path like '#/$defs/MyModel'
                def_name = ref_path.split('/')[-1]
                # Get the definition and recursively resolve its own refs
                return resolve_refs(defs[def_name])
            else:
                # Recursively process dictionary values
                return {k: resolve_refs(v) for k, v in node.items()}
        elif isinstance(node, list):
            # Recursively process list items
            return [resolve_refs(item) for item in node]
        else:
            # Return primitive values as-is
            return node

    # Start the resolving process on the main schema
    inlined_schema = resolve_refs(schema)
    return inlined_schema

def get_user_input(user_messages) -> str:
    # 提取用户消息内容
    if isinstance(user_messages, list) and len(user_messages) > 0:
        # 获取最后一条用户消息
        last_message = user_messages[-1]
        # print('last_message', last_message)
        if hasattr(last_message, 'content'):
            # 如果是 HumanMessage 对象
            user_input = str(last_message.content)
        elif isinstance(last_message, dict) and "content" in last_message:
            user_input = str(last_message["content"])
        else:
            user_input = str(last_message)
    else:
        user_input = str(user_messages)
    
    # print(f"User input: {user_input}")
    return user_input
