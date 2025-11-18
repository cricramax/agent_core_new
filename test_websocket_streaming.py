#!/usr/bin/env python3
"""
Test script for WebSocket streaming functionality.

This script tests the core streaming features without requiring a frontend client.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from dotenv import load_dotenv
load_dotenv()

from video_agents_example.video_agent import video_agent
from server.services.agent_stream_service import AgentStreamService
from langchain_core.runnables import RunnableConfig


async def test_streaming():
    """Test the streaming functionality."""
    
    print("🧪 Testing WebSocket Streaming Service")
    print("=" * 50)
    
    # Initialize service with existing checkpointer
    agent_service = AgentStreamService(video_agent.checkpointer)
    
    # Test session ID
    test_session_id = "test_1234567"
    
    print(f"📍 Test Session ID: {test_session_id}")
    
    # Load existing state
    print("\n1️⃣ Loading existing session state...")
    session_state = await agent_service.get_session_state(test_session_id)
    
    print(f"   📚 Messages: {len(session_state['conversation']['messages'])}")
    print(f"   ✅ TODOs: {len(session_state['conversation']['current_todos'])}")
    print(f"   📁 Files: {len(session_state['workspace']['files'])}")
    
    # Test message
    test_message = "Create a short video about machine learning basics"
    
    print(f"\n2️⃣ Sending test message: '{test_message}'")
    print("   Streaming response:")
    print("   " + "-" * 40)
    
    # Create config
    config = RunnableConfig({"configurable": {"thread_id": test_session_id}})
    
    # Mock WebSocket broadcast function
    async def mock_broadcast(session_id, canvas_id, data):
        # Just log the broadcast data
        data_type = data.get('type', 'unknown')
        if data_type == 'token':
            print(data.get('content', ''), end='', flush=True)
        elif data_type == 'todos_update':
            print(f"\n   📝 TODOs updated: {len(data.get('todos', []))}")
        elif data_type == 'tool_message':
            print(f"\n   🔧 {data.get('tool_name', 'Tool')}: {data.get('content', '')[:100]}...")
        elif data_type == 'sub_agent_step':
            print(f"\n   🔄 Sub-agent: {data.get('step', 'unknown')} - {data.get('message', '')}")
        elif data_type == 'workspace_files_update':
            print(f"\n   📁 Workspace updated: {len(data.get('files', {}))} files")
        elif data_type == 'response_complete':
            print("\n   ✅ Response complete!")
    
    # Temporarily replace the broadcast function for testing
    original_broadcast = agent_service.__class__.__module__
    
    try:
        # Override broadcast function in websocket_service
        import server.services.websocket_service as ws_service
        original_broadcast_func = ws_service.broadcast_session_update
        ws_service.broadcast_session_update = mock_broadcast
        
        # Stream the response
        stream_count = 0
        async for stream_data in agent_service.stream_agent_response(
            agent=video_agent,
            user_input=test_message,
            session_id=test_session_id,
            config=config
        ):
            stream_count += 1
            
            # Handle different stream types
            if stream_data.get('type') == 'response_complete':
                break
        
        print(f"\n\n3️⃣ Streaming completed! Processed {stream_count} stream events")
        
        # Check final state
        print("\n4️⃣ Checking final session state...")
        final_state = await agent_service.get_session_state(test_session_id)
        
        print(f"   📚 Final messages: {len(final_state['conversation']['messages'])}")
        print(f"   ✅ Final TODOs: {len(final_state['conversation']['current_todos'])}")
        print(f"   📁 Final files: {len(final_state['workspace']['files'])}")
        
        # Show some file details
        if final_state['workspace']['files']:
            print("\n   📄 Workspace files:")
            for file_info in final_state['workspace']['files']:
                file_path = file_info['file_path']
                content_length = len(file_info['content'])
                file_type = file_info['file_type']
                print(f"      - {file_path} ({file_type}, {content_length} chars)")
        
        # Restore original broadcast function
        ws_service.broadcast_session_update = original_broadcast_func
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Restore original broadcast function
        try:
            ws_service.broadcast_session_update = original_broadcast_func
        except:
            pass


async def test_session_persistence():
    """Test session persistence across multiple interactions."""
    
    print("\n🔄 Testing Session Persistence")
    print("=" * 50)
    
    agent_service = AgentStreamService(video_agent.checkpointer)
    test_session_id = "persistence_test_456"
    
    # First interaction
    print("1️⃣ First interaction...")
    config = RunnableConfig({"configurable": {"thread_id": test_session_id}})
    
    # Mock broadcast for this test
    import server.services.websocket_service as ws_service
    original_broadcast_func = ws_service.broadcast_session_update
    
    async def silent_broadcast(session_id, canvas_id, data):
        pass
    
    ws_service.broadcast_session_update = silent_broadcast
    
    try:
        # First message
        async for _ in agent_service.stream_agent_response(
            agent=video_agent,
            user_input="Create an outline for a video about Python programming",
            session_id=test_session_id,
            config=config
        ):
            pass
        
        # Check state after first interaction
        state1 = await agent_service.get_session_state(test_session_id)
        print(f"   After first: {len(state1['conversation']['messages'])} messages, {len(state1['workspace']['files'])} files")
        
        # Second interaction
        print("\n2️⃣ Second interaction...")
        async for _ in agent_service.stream_agent_response(
            agent=video_agent,
            user_input="Now create scripts for the first segment",
            session_id=test_session_id,
            config=config
        ):
            pass
        
        # Check state after second interaction
        state2 = await agent_service.get_session_state(test_session_id)
        print(f"   After second: {len(state2['conversation']['messages'])} messages, {len(state2['workspace']['files'])} files")
        
        # Verify persistence
        if len(state2['conversation']['messages']) > len(state1['conversation']['messages']):
            print("✅ Session persistence working correctly!")
        else:
            print("❌ Session persistence may have issues")
            
    finally:
        # Restore original broadcast function
        ws_service.broadcast_session_update = original_broadcast_func


async def main():
    """Run all tests."""
    try:
        await test_streaming()
        await test_session_persistence()
        
        print("\n🎉 All tests completed!")
        print("\n💡 To start the WebSocket server, run:")
        print("   python start_server.py")
        print("\n💡 Then open: http://localhost:8000/static/index.html")
        
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 