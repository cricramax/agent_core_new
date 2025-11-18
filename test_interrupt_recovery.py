"""
测试 LangGraph 智能体的中断和恢复机制

这个脚本用于测试：
1. 智能体在执行过程中被中断后的状态保存
2. 子智能体的执行记录是否被保存
3. 大模型调用是否正确停止
4. 重新启动后是否能从正确的状态恢复
"""

import asyncio
import signal
import sys
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from xlangguage_nodes.xlangguage_agent import xlangguage_agent
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

class InterruptTestManager:
    def __init__(self):
        self.agent = xlangguage_agent
        self.config = RunnableConfig({"configurable": {"thread_id": "interrupt_test_123"}})
        self.interrupted = False
        self.checkpoint_data = None
        self.execution_log = []
        
    def setup_signal_handler(self):
        """设置信号处理器来捕获 Ctrl+C"""
        def signal_handler(sig, frame):
            print("\n🛑 检测到中断信号 (Ctrl+C)")
            self.interrupted = True
            self.save_checkpoint()
            print("💾 状态已保存，程序即将退出...")
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        
    def save_checkpoint(self):
        """保存当前的检查点数据"""
        try:
            # 获取当前状态
            current_state = self.agent.get_state(self.config)
            self.checkpoint_data = {
                'timestamp': datetime.now().isoformat(),
                'thread_id': self.config["configurable"]["thread_id"],
                'state': current_state.values if hasattr(current_state, 'values') else None,
                'next_steps': current_state.next if hasattr(current_state, 'next') else None,
                'execution_log': self.execution_log,
                'interrupted': True
            }
            
            # 保存到文件
            checkpoint_file = Path("checkpoint_data.json")
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.checkpoint_data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"✅ 检查点数据已保存到 {checkpoint_file}")
            
        except Exception as e:
            print(f"❌ 保存检查点时出错: {e}")
    
    def load_checkpoint(self):
        """加载之前保存的检查点数据"""
        checkpoint_file = Path("checkpoint_data.json")
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    self.checkpoint_data = json.load(f)
                print("✅ 成功加载之前的检查点数据")
                print(f"   时间戳: {self.checkpoint_data.get('timestamp')}")
                print(f"   线程ID: {self.checkpoint_data.get('thread_id')}")
                print(f"   是否被中断: {self.checkpoint_data.get('interrupted')}")
                return True
            except Exception as e:
                print(f"❌ 加载检查点时出错: {e}")
                return False
        else:
            print("ℹ️ 未找到之前的检查点文件")
            return False
    
    def log_execution(self, event_type, data):
        """记录执行事件"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'data': data
        }
        self.execution_log.append(log_entry)
        
    async def test_normal_execution(self, user_input):
        """测试正常执行流程"""
        print("🚀 开始正常执行测试...")
        self.log_execution('test_start', {'type': 'normal', 'input': user_input})
        
        buffered_text = ""
        tool_call_chunks = {}
        printed_tool_calls = set()
        
        try:
            async for chunk in self.agent.astream(
                {"messages": user_input},
                config=self.config,
                stream_mode=["messages", "updates", "custom"]
            ):
                if self.interrupted:
                    break
                    
                stream_type, data = chunk
                self.log_execution('stream_chunk', {'stream_type': stream_type})
                
                if stream_type == "messages":
                    message_chunk, metadata = data
                    
                    # 处理助手文本内容
                    if hasattr(message_chunk, 'content') and message_chunk.content:
                        current = message_chunk.content
                        max_lcp = min(len(buffered_text), len(current))
                        i = 0
                        while i < max_lcp and buffered_text[i] == current[i]:
                            i += 1
                        delta = current[i:]
                        if delta:
                            print(delta, end="", flush=True)
                        buffered_text = current
                    
                    # 处理工具调用
                    addkw = getattr(message_chunk, 'additional_kwargs', {}) or {}
                    for tc in (addkw.get('tool_calls') or []):
                        name = (tc.get('function') or {}).get('name') or tc.get('name')
                        args = (tc.get('function') or {}).get('arguments') or tc.get('args')
                        if name and args:
                            sig = f"{name}|{args}"
                            if sig not in printed_tool_calls:
                                print(f"\n🔧 调用工具: {name}")
                                print(f"   参数: {args}")
                                printed_tool_calls.add(sig)
                                self.log_execution('tool_call', {'name': name, 'args': args})
                    
                    # 检查完成状态
                    if getattr(message_chunk, 'response_metadata', {}).get('finish_reason') == 'stop':
                        print("\n", "--------------------------------")
                        self.log_execution('execution_complete', {'reason': 'stop'})
                        
                elif stream_type == "custom":
                    # 处理子智能体事件
                    if isinstance(data, dict) and 'subagent' in data:
                        evt = data['subagent']
                        et = evt.get('type')
                        self.log_execution('subagent_event', evt)
                        
                        if et == 'start':
                            print(f"\n=== 启动子智能体: {evt.get('name')} ===")
                        elif et == 'content':
                            txt = evt.get('text', '')
                            if txt:
                                print(txt, end="", flush=True)
                        elif et == 'tool_call':
                            print(f"\n  🔧 子智能体调用工具: {evt.get('name')}")
                        elif et == 'stop':
                            print("\n=== 子智能体任务完成 ===")
                            
        except KeyboardInterrupt:
            print("\n🛑 执行被用户中断")
            self.interrupted = True
        except Exception as e:
            print(f"\n❌ 执行过程中出错: {e}")
            self.log_execution('execution_error', {'error': str(e)})
            
    async def test_recovery(self):
        """测试恢复机制"""
        if not self.checkpoint_data:
            print("❌ 没有检查点数据可以恢复")
            return False
            
        print("🔄 开始恢复测试...")
        
        try:
            # 使用相同的线程ID创建新的config
            recovery_config = RunnableConfig({
                "configurable": {"thread_id": self.checkpoint_data.get('thread_id')}
            })
            
            # 获取当前状态
            current_state = self.agent.get_state(recovery_config)
            
            print("📊 当前状态信息:")
            print(f"   状态存在: {current_state is not None}")
            if current_state and hasattr(current_state, 'values'):
                print(f"   消息数量: {len(current_state.values.get('messages', []))}")
                print(f"   文件数量: {len(current_state.values.get('files', {}))}")
                print(f"   待办事项: {len(current_state.values.get('todos', []))}")
            
            # 尝试继续执行
            print("\n🔄 尝试从中断点继续执行...")
            user_input = input("请输入新的指令 (或按回车继续之前的任务): ").strip()
            if not user_input:
                user_input = "继续之前的任务"
                
            await self.test_normal_execution(user_input)
            
            return True
            
        except Exception as e:
            print(f"❌ 恢复过程中出错: {e}")
            return False
    
    def print_execution_summary(self):
        """打印执行摘要"""
        print("\n" + "="*50)
        print("📋 执行摘要")
        print("="*50)
        
        tool_calls = [log for log in self.execution_log if log['type'] == 'tool_call']
        subagent_events = [log for log in self.execution_log if log['type'] == 'subagent_event']
        
        print(f"总执行事件数: {len(self.execution_log)}")
        print(f"工具调用次数: {len(tool_calls)}")
        print(f"子智能体事件数: {len(subagent_events)}")
        
        if tool_calls:
            print("\n🔧 工具调用记录:")
            for i, call in enumerate(tool_calls, 1):
                data = call['data']
                print(f"  {i}. {data['name']} - {call['timestamp']}")
        
        subagent_starts = [evt for evt in subagent_events 
                          if evt['data'].get('type') == 'start']
        if subagent_starts:
            print("\n🤖 子智能体启动记录:")
            for i, start in enumerate(subagent_starts, 1):
                data = start['data']
                print(f"  {i}. {data.get('name')} - {start['timestamp']}")

async def main():
    """主测试函数"""
    test_manager = InterruptTestManager()
    test_manager.setup_signal_handler()
    
    print("🔍 LangGraph 智能体中断恢复测试")
    print("="*50)
    
    # 检查是否有之前的检查点
    has_checkpoint = test_manager.load_checkpoint()
    
    if has_checkpoint:
        print("\n选择测试模式:")
        print("1. 从检查点恢复执行")
        print("2. 开始新的测试")
        choice = input("请选择 (1/2): ").strip()
        
        if choice == "1":
            success = await test_manager.test_recovery()
            if not success:
                print("恢复失败，开始新的测试...")
                await run_new_test(test_manager)
        else:
            await run_new_test(test_manager)
    else:
        await run_new_test(test_manager)
    
    test_manager.print_execution_summary()

async def run_new_test(test_manager):
    """运行新的测试"""
    print("\n💡 提示: 你可以在执行过程中按 Ctrl+C 来中断智能体")
    print("      中断后状态会被保存，下次运行时可以选择恢复")
    
    user_input = input("\n请输入测试指令: ").strip()
    if not user_input:
        user_input = "请帮我分析一下系统建模的基本步骤，并创建一个简单的待办事项列表"
    
    await test_manager.test_normal_execution(user_input)

if __name__ == "__main__":
    asyncio.run(main()) 