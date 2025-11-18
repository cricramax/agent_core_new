# from langchain_anthropic import ChatAnthropic


# def get_default_model():
#     return ChatAnthropic(model_name="claude-sonnet-4-20250514", max_tokens=64000)

import os 
from langchain_openai import ChatOpenAI

def get_default_model():
    return ChatOpenAI(model="qwen-omni-turbo", max_tokens=64000, temperature=0.1, \
        api_key=os.environ["QWEN_API_KEY"], base_url=os.environ["QWEN_BASE_URL"])