import requests
import httpx
import os
from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import JSONResponse
from langchain_core.tools import tool
from typing import Annotated
from langchain_core.tools import InjectedToolCallId
from langgraph.config import get_stream_writer
from langgraph.types import Command
from langchain_core.messages import ToolMessage


# 接口地址 :https://gateway.cnki.net/openx/admin/login/jwt

# 请求方式: POST

# 请求数据类型:application/x-www-form-urlencoded

# 接口描述: 客户端模式获取jwttoken

# 应用名称	AppId	ApiKey	SecretKey	应用类型 	状态	审核状态	
# test_bh	

AppID = "1752565762461"	
ApiKey = "FVXKWxXJJeKAjoHh"	
SecretKey = "VRfHSGsDLlNWOUuWBVjz6Eg94J"
grant_type = "client_credentials"

UserID = "33dd6b23-df2e-49f1-829f-454cd6ba4205"
URL = "https://gateway.cnki.net/openx/admin/login/jwt"
Chat_URL = "https://gateway.cnki.net/openx/bigmodel/ai/qkwd/v1/chat"

USER_DATA_DIR = os.environ["USER_DATA_DIR"]
os.makedirs(USER_DATA_DIR, exist_ok=True)

def get_jwt_token():
    """获取JWT Token"""
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "app_id": AppID,
        "client_id": ApiKey,
        "grant_type": grant_type
    }

    response = requests.post(URL, headers=headers, data=data)
    if response.status_code == 200:
        # return response.json().get("content")
        return response.json()
    return None

async def get_jwt_token_async():
    """异步获取JWT Token"""
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "app_id": AppID,
        "client_id": ApiKey,
        "grant_type": grant_type
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(URL, headers=headers, data=data)
        if response.status_code == 200:
            return response.json()
    return None

# 使用异步版本获取token
token = get_jwt_token()


# @app.route('/cnki_qa', methods=['POST'])
# @router.post("/cnki_qa")
@tool
def cnki_search(
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId]):
    """
    this tool can search the cnki database for papers related to the query and summarize the papers to form an answer for the query.
    you can use this tool to get more related information for you to do your job.
    
    - Arg:
        - query: str
            - 查询内容
    """
    if not query:
        return f"Missing 'query' parameter"

    print(f"收到查询请求: {query}")

    if not token:
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to retrieve JWT Token - token is None"}
        )
    
    JWT = token.get("content", {}).get("access_token")
    Authorization = f"Bearer {JWT}" if JWT else None
    if not Authorization:
        return f"Failed to retrieve JWT Token - no access_token"
    
    print(f"成功获取JWT Token: {JWT[:20]}...")

    # Prepare request
    headers = {
        "Authorization": Authorization,
        "Content-Type": "application/json"
    }
    Chat_URL = "https://gateway.cnki.net/openx/bigmodel/ai/qkwd/v1/chat"
    payload = {
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ],
        "source": "xaiFullLibraryQA",
        "userid": UserID,
        "moduleVersionStr": "r_cnki_deepseek_r1",
        "netSearchEnabled": False,
        "resultType": "NORMAL_CONTENT",
        "ifSse": True
    }

    import json

    answer = ""
    try:
        response = requests.post(Chat_URL, headers=headers, json=payload, stream=True)
        if response.status_code == 200:
            for line in response.iter_lines(decode_unicode=True):
                if line and line.startswith("data:"):
                    try:
                        import json
                        content_json = line[5:].strip()
                        data_obj = json.loads(content_json)
                        data_content = data_obj.get("content", "")
                        answer += data_content
                        # print(data_content, end="", flush=True)
                    except Exception as e:
                        print("\nerror:", e)
            if answer:
                print(f"answer: {answer}")
                file_path = f"cnki_search_{query}"
                # 获取</think>之后的回答作为answer_message
                # 如果</think>不存在，则answer_message为answer原文
                think_end = answer.find("</think>")
                if think_end != -1:
                    # 获取</think>之后的内容
                    answer_message = answer[think_end + len("</think>") :]
                else:
                    answer_message = answer
                answer_message = answer_message.lstrip("\n")
                answer = answer_message
                return Command(
                            update={
                                "files": {
                                    file_path: answer
                                },
                                "messages": [
                                    ToolMessage(
                                        f"search answer: {answer_message}. \n Updated this search result in file: {file_path}",
                                         tool_call_id=tool_call_id)
                                ],
                            }
                        )
            return f"No valid response content received, response is {response.text}"
        else:
            return f"HTTP error: {response.status_code}"
    except httpx.TimeoutException:
        return f"Request timeout"
    except Exception as e:
        return f"Request failed: {str(e)}"


import json
import datetime
def save_response_to_file(response, \
    filename=os.path.join(USER_DATA_DIR, f"response_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")):
    """将响应保存到文件"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(response, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    result = cnki_search("什么是人工智能？")
    print(result)