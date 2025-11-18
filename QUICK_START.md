# 🚀 Quick Start - DeepAgent Video Creator WebSocket Streaming

## 📋 概述

您的视频生成智能体现在支持完整的 WebSocket 流式输出，包括：

- ✅ **实时流式响应**: LLM 令牌级别的实时输出
- ✅ **TODO 实时更新**: 智能体任务进度实时可视化  
- ✅ **子智能体步骤**: outline-agent 和 scripts-agent 的关键步骤流式输出
- ✅ **工作区文件管理**: 脚本、大纲文件实时更新
- ✅ **会话持久化**: 使用现有的 MongoDBSaver 存储和恢复会话
- ✅ **历史加载**: 重新打开会话时自动加载对话历史和工作区内容

## 🏃‍♂️ 立即开始

### 1. 安装依赖

```bash
cd deep_agent_lx
pip install -r server/requirements.txt
```

### 2. 启动 WebSocket 服务器

```bash
# 方式 1: 使用便捷启动脚本
python start_server.py

# 方式 2: 直接运行服务器
cd server && python app.py
```

服务器启动后会显示：
- WebSocket 端点: `ws://localhost:8000/socket.io/`
- 测试客户端: `http://localhost:8000/static/index.html`
- API 文档: `http://localhost:8000/docs`

### 3. 测试功能

#### 选项 A: 浏览器测试客户端
访问 http://localhost:8000/static/index.html

#### 选项 B: 控制台模式
```bash
python websocket_main.py
```

#### 选项 C: 运行测试脚本
```bash
python test_websocket_streaming.py
```

## 💡 使用示例

### 视频创建工作流

1. **发送消息**: "创建一个5分钟关于人工智能的教育视频"

2. **观察实时输出**:
   ```
   🤖 Agent: 我来帮您创建一个关于人工智能的教育视频...
   
   📝 TODOs Updated (3):
     1. ⏳ 创建视频大纲 [pending]
     2. ⏳ 编写各片段脚本 [pending] 
     3. ⏳ 优化脚本内容 [pending]
   
   🔄 Sub-agent [Writing File]: Creating new file: outline_files/ai_video_outline.json
   🔧 outline-agent: Created comprehensive video outline with 5 segments...
   
   📁 Workspace Updated - 1 files
     📄 outline_files/ai_video_outline.json
   
   🔄 Sub-agent [Editing File]: Editing file: scripts_files/script_segment_1.txt
   🔧 scripts-agent: Generated engaging script for introduction segment...
   
   ✅ Response complete!
   ```

### WebSocket 客户端集成

```javascript
const socket = io('ws://localhost:8000');

// 连接并加入会话
socket.on('connect', () => {
    socket.emit('join_session', {
        session_id: 'my-video-project',
        canvas_id: 'main-canvas'
    });
});

// 接收历史状态
socket.on('session_state_loaded', (data) => {
    loadConversationHistory(data.conversation.messages);
    updateTodos(data.conversation.current_todos);
    updateWorkspace(data.workspace.files);
});

// 处理实时流式更新
socket.on('session_update', (data) => {
    switch (data.type) {
        case 'token':
            // 实时显示 AI 文本生成
            appendToChat(data.content);
            break;
            
        case 'todos_update':
            // 更新 TODO 列表
            updateTodoList(data.todos);
            break;
            
        case 'sub_agent_step':
            // 显示子智能体步骤
            showSubAgentActivity(data.step, data.message);
            break;
            
        case 'workspace_files_update':
            // 更新工作区文件
            updateWorkspaceFiles(data.files);
            break;
    }
});

// 发送消息
function sendMessage(message) {
    socket.emit('send_message', {
        session_id: 'my-video-project',
        message: message
    });
}
```

## 🎯 核心功能

### 1. 流式输出类型

| 类型 | 描述 | 示例用途 |
|------|------|----------|
| `token` | LLM 生成的文本令牌 | 实时显示 AI 回复 |
| `todos_update` | TODO 列表更新 | 任务进度可视化 |
| `tool_message` | 子智能体工具输出 | 显示子智能体完成的任务 |
| `sub_agent_step` | 子智能体关键步骤 | 详细的操作进度 |
| `workspace_files_update` | 工作区文件更新 | 文件创建/编辑通知 |
| `response_complete` | 响应完成 | 标记对话结束 |

### 2. 会话管理

- **自动持久化**: 使用 LangGraph 的 MongoDBSaver
- **历史恢复**: 重新连接时自动加载历史
- **多会话支持**: 每个 session_id 独立管理

### 3. 工作区文件

视频生成过程中创建的文件会实时同步到前端：

- `outline_files/outline.json` - 视频大纲
- `scripts_files/script_segment_*.txt` - 各片段脚本
- `research_files/*` - 研究资料（如果有）

## 🔧 技术细节

### MongoDB 存储结构

系统利用 LangGraph 的 MongoDBSaver，状态结构：

```python
{
    "messages": [...],      # 对话历史
    "todos": [...],         # 当前 TODO 列表
    "files": {              # 工作区文件系统
        "file_path": ["content_v1", "content_v2", ...]
    }
}
```

### 流式模式配置

```python
stream_mode=["messages", "updates", "custom"]
```

- `messages`: LLM 令牌流式输出
- `updates`: 状态更新（TODOs、文件等）
- `custom`: 自定义流式数据（子智能体步骤）

## 🐛 故障排除

### 常见问题

1. **连接失败**
   - 确保服务器正在运行
   - 检查端口 8000 是否被占用

2. **历史加载失败**
   - 检查 MongoDB 连接
   - 验证 session_id 格式

3. **流式输出中断**
   - 检查网络连接
   - 查看服务器日志

### 日志查看

服务器日志会显示详细的连接和处理信息：

```
Client abc123 connected
Client abc123 joining session my-session
Session state loaded for my-session: 5 messages, 3 files
Processing message from abc123 in session my-session: Create a video...
```

## 🎬 下一步

现在您可以：

1. **集成到现有前端**: 使用提供的 WebSocket API
2. **自定义流式输出**: 在子智能体中添加更多 `get_stream_writer()` 调用
3. **扩展工作区功能**: 添加文件下载、预览等功能
4. **优化性能**: 根据需要调整流式输出频率

享受您的实时视频生成智能体！🚀 