"""
简化版的 LangGraph 智能体中断恢复测试

测试重点：
1. 检查点的保存和加载
2. 状态的持久化
3. 子智能体执行状态的保存
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from xlangguage_nodes.xlangguage_agent import xlangguage_agent

load_dotenv()

async def test_checkpoint_functionality():
    """测试检查点功能"""
    print("🔍 测试检查点功能")
    print("="*40)
    
    # 创建智能体和配置
    agent = xlangguage_agent
    config = RunnableConfig({"configurable": {"thread_id": "checkpoint_test_456"}})
    
    print("1️⃣ 测试初始状态...")
    initial_state = agent.get_state(config)
    print(f"   初始状态存在: {initial_state is not None}")
    if initial_state and hasattr(initial_state, 'values'):
        print(f"   初始消息数: {len(initial_state.values.get('messages', []))}")
    
    print("\n2️⃣ 发送第一条消息...")
    # 发送第一条消息
    result1 = await agent.ainvoke(
        {"messages": "你好，请介绍一下你的功能"},
        config=config
    )
    print(f"   响应长度: {len(result1.get('messages', []))}")
    
    # 检查状态
    state_after_first = agent.get_state(config)
    print(f"   状态更新后消息数: {len(state_after_first.values.get('messages', []))}")
    
    print("\n3️⃣ 发送需要调用工具的消息...")
    # 发送一个需要调用工具的消息
    result2 = await agent.ainvoke(
        {"messages": "请帮我创建一个关于系统建模的待办事项列表"},
        config=config
    )
    
    # 检查最终状态
    final_state = agent.get_state(config)
    print(f"   最终消息数: {len(final_state.values.get('messages', []))}")
    print(f"   待办事项数: {len(final_state.values.get('todos', []))}")
    print(f"   文件数: {len(final_state.values.get('files', {}))}")
    
    # 保存状态信息
    checkpoint_data = {
        'timestamp': datetime.now().isoformat(),
        'thread_id': config["configurable"]["thread_id"],
        'message_count': len(final_state.values.get('messages', [])),
        'todos_count': len(final_state.values.get('todos', [])),
        'files_count': len(final_state.values.get('files', {})),
        'last_message': final_state.values.get('messages', [])[-1].content if final_state.values.get('messages') else None
    }
    
    # 保存到文件
    with open('simple_checkpoint.json', 'w', encoding='utf-8') as f:
        json.dump(checkpoint_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ 检查点数据已保存")
    return checkpoint_data

async def test_state_recovery():
    """测试状态恢复"""
    print("\n🔄 测试状态恢复")
    print("="*40)
    
    # 加载之前的检查点
    checkpoint_file = Path('simple_checkpoint.json')
    if not checkpoint_file.exists():
        print("❌ 未找到检查点文件，请先运行检查点测试")
        return
    
    with open(checkpoint_file, 'r', encoding='utf-8') as f:
        checkpoint_data = json.load(f)
    
    print("📊 加载的检查点信息:")
    print(f"   时间戳: {checkpoint_data['timestamp']}")
    print(f"   线程ID: {checkpoint_data['thread_id']}")
    print(f"   消息数: {checkpoint_data['message_count']}")
    print(f"   待办事项数: {checkpoint_data['todos_count']}")
    print(f"   文件数: {checkpoint_data['files_count']}")
    
    # 使用相同的线程ID创建新的会话
    agent = xlangguage_agent
    recovery_config = RunnableConfig({
        "configurable": {"thread_id": checkpoint_data['thread_id']}
    })
    
    print("\n🔍 检查恢复后的状态...")
    recovered_state = agent.get_state(recovery_config)
    
    if recovered_state and hasattr(recovered_state, 'values'):
        current_messages = len(recovered_state.values.get('messages', []))
        current_todos = len(recovered_state.values.get('todos', []))
        current_files = len(recovered_state.values.get('files', {}))
        
        print(f"   恢复后消息数: {current_messages}")
        print(f"   恢复后待办事项数: {current_todos}")
        print(f"   恢复后文件数: {current_files}")
        
        # 验证状态是否一致
        state_consistent = (
            current_messages == checkpoint_data['message_count'] and
            current_todos == checkpoint_data['todos_count'] and
            current_files == checkpoint_data['files_count']
        )
        
        if state_consistent:
            print("✅ 状态恢复成功！数据一致")
        else:
            print("⚠️ 状态数据不完全一致")
        
        # 测试继续对话
        print("\n💬 测试继续对话...")
        continue_result = await agent.ainvoke(
            {"messages": "请总结一下我们之前讨论的内容"},
            config=recovery_config
        )
        
        print("✅ 成功从恢复的状态继续对话")
        
    else:
        print("❌ 无法恢复状态")

async def test_subagent_state_persistence():
    """测试子智能体状态持久化"""
    print("\n🤖 测试子智能体状态持久化")
    print("="*40)
    
    agent = xlangguage_agent
    config = RunnableConfig({"configurable": {"thread_id": "subagent_test_789"}})
    
    print("1️⃣ 发送需要调用子智能体的任务...")
    
    # 这个任务应该会触发子智能体
    test_message = "请帮我分析一下需求工程的基本流程，并生成相关的文档"
    
    try:
        # 使用流式处理来观察子智能体的执行
        subagent_called = False
        tool_calls = []
        
        async for chunk in agent.astream(
            {"messages": test_message},
            config=config,
            stream_mode=["messages", "updates", "custom"]
        ):
            stream_type, data = chunk
            
            if stream_type == "messages":
                message_chunk, metadata = data
                
                # 检查工具调用
                addkw = getattr(message_chunk, 'additional_kwargs', {}) or {}
                for tc in (addkw.get('tool_calls') or []):
                    name = (tc.get('function') or {}).get('name') or tc.get('name')
                    if name == 'task':  # 这是调用子智能体的工具
                        subagent_called = True
                        tool_calls.append(tc)
                        print(f"🔧 检测到子智能体调用: {name}")
            
            elif stream_type == "custom":
                if isinstance(data, dict) and 'subagent' in data:
                    evt = data['subagent']
                    print(f"🤖 子智能体事件: {evt.get('type')} - {evt.get('name', 'unknown')}")
        
        # 检查最终状态
        final_state = agent.get_state(config)
        if final_state and hasattr(final_state, 'values'):
            messages = final_state.values.get('messages', [])
            print(f"\n📊 执行完成后状态:")
            print(f"   消息总数: {len(messages)}")
            print(f"   工具调用数: {len(tool_calls)}")
            print(f"   子智能体被调用: {subagent_called}")
            
            # 保存子智能体测试的状态
            subagent_checkpoint = {
                'timestamp': datetime.now().isoformat(),
                'thread_id': config["configurable"]["thread_id"],
                'subagent_called': subagent_called,
                'tool_calls_count': len(tool_calls),
                'final_message_count': len(messages)
            }
            
            with open('subagent_checkpoint.json', 'w', encoding='utf-8') as f:
                json.dump(subagent_checkpoint, f, ensure_ascii=False, indent=2, default=str)
            
            print("✅ 子智能体测试完成，状态已保存")
        
    except Exception as e:
        print(f"❌ 子智能体测试出错: {e}")

async def main():
    """主测试函数"""
    print("🧪 简化版 LangGraph 智能体中断恢复测试")
    print("="*50)
    
    print("\n选择测试项目:")
    print("1. 基本检查点功能测试")
    print("2. 状态恢复测试")
    print("3. 子智能体状态持久化测试")
    print("4. 运行所有测试")
    
    choice = input("\n请选择 (1-4): ").strip()
    
    if choice == "1":
        await test_checkpoint_functionality()
    elif choice == "2":
        await test_state_recovery()
    elif choice == "3":
        await test_subagent_state_persistence()
    elif choice == "4":
        print("🚀 运行所有测试...")
        await test_checkpoint_functionality()
        await test_state_recovery()
        await test_subagent_state_persistence()
    else:
        print("无效选择，运行所有测试...")
        await test_checkpoint_functionality()
        await test_state_recovery()
        await test_subagent_state_persistence()
    
    print("\n🎉 测试完成！")

if __name__ == "__main__":
    asyncio.run(main()) 