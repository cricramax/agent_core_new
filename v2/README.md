## DeepAgent XLanguage v2 架构与接口文档

本文件详细说明 v2 的后端 API、SSE 流式协议、前端消息分类/显示规则、工具调用生命周期、对话历史管理、子智能体分流显示策略，以及当前已知问题与改进建议。

### 核心目标
- 对话历史管理：支持多线程 Thread 列表、创建/删除、加载对话消息与文件。
- 实时对话与消息推送：使用 SSE（Server-Sent Events）向前端流式推送主智能体与子智能体事件。
- 消息分类与显示：区分用户消息、主智能体消息、子智能体消息；工具调用消息与工具返回结果分别展示；每段回复或工具阶段结束后开启新的消息气泡。
- 文件工作区同步：工具更新文件后，工作区与主对话需要收到并展示文件变更摘要。

---

## 后端 API（FastAPI）
服务入口：`v2/server/app.py`

- GET `/api/threads`
  - 描述：获取用户的对话 Thread 列表。
  - Query：`user_id?`（目前可缺省，默认 `x_lab`）。
  - 返回：`ThreadInfo[]`（字段见 types）。

- POST `/api/threads`
  - 描述：创建一个新 Thread。
  - Body：`{ title?: string, user_id?: string }`（前端当前只传 `title`）。
  - 返回：`ThreadInfo`。

- DELETE `/api/threads/{thread_id}`
  - 描述：删除 Thread 及其消息。
  - 返回：`{ success: true }`。

- GET `/api/threads/{thread_id}/messages`
  - 描述：获取指定 Thread 的全部主智能体消息与文件快照。
  - 返回：`{ messages: ChatMessage[], files: Record<string, string[]>, thread_id: string }`。
  - 说明：仅包含主智能体（`user | assistant | tool`）的消息；根据 UI 策略过滤隐藏部分工具消息（如 `write_file` 参数内容）。

- POST `/api/chat/stream`
  - 描述：开启与主智能体的流式对话（SSE）。
  - Body：`{ thread_id: string, message: string, user_id?: string }`。
  - 返回：SSE 流，`text/event-stream`。
  - 并发：同一 Thread 同时只允许一个流存在，存在则返回 `409`。

- POST `/api/chat/stop`
  - 描述：停止指定 Thread 的正在进行的流。
  - Body：`{ thread_id: string }`。
  - 返回：`{ success: true, stopped: true }`。

- GET `/api/health`
  - 描述：健康检查与 Mongo 连接状态。

### 数据模型（后端）
- `ChatMessage`（后端内部）：`{ role, content, timestamp, tool_calls?, message_type? }`
- `ThreadInfo`：`{ thread_id, title, created_at, last_message_at?, message_count }`
- `ChatRequest`：`{ thread_id?, message }`

### 本地会话存储
文件：`v2/server/local_storage.py`
- 作用：在无鉴权前提下，以 `user_{user_id}.json` 持久化每个用户的 Thread 列表、时间戳等元数据。
- 方法：
  - `add_thread_for_user(thread_id, title, user_id?)`
  - `update_thread_activity(thread_id, user_id?)`
  - `get_threads_for_user(user_id?)`
  - `remove_thread_for_user(thread_id, user_id?)`
  - `thread_belongs_to_user(thread_id, user_id?)`

---

## SSE 协议

后端统一通过 `_sse_format(event_type, data)` 推送事件。实际报文形如：
```
event: <type>
data: {"type":"<type>","data":<payload>}

```
前端当前实现忽略 `event:` 行，统一解析 `data` 中的 `type` 字段。

### 事件类型与负载
- `message`
  - 负载（`data`）为主智能体的分片消息：
    - `{ content, type, additional_kwargs, response_metadata }`
    - `type` 常见：`ai | human | tool`（后端已归一化为上游类型，前端用作判断）
    - `additional_kwargs.tool_call_chunks?`：流式工具名/参数片段
    - `additional_kwargs.tool_calls?`：已成型的工具调用项
    - `response_metadata.finish_reason?`：`tool_calls | stop` 等
- `update`
  - 负载：LangGraph 节点更新。前端关心 `files`：`Record<string, string[]>`。
- `subagent`
  - 负载：子智能体事件，形如：
    - `{ type: 'start'|'stop'|'chunk'|'content'|'tool_call'|'message'|'files_update', name?, description?, text?, stream_type?, data?, tool_calls?, files? }`
  - 用于右侧工作区独立展示，不进入主对话。
- `stop`
  - 负载：`{ reason: 'interrupted' }`（用户中断时）。
- `error`
  - 负载：`{ error: string }`。

---

## 前端数据类型与通道
文件：`v2/frontend/src/types.ts`
- `ChatMessage`（前端）
  - `{ role: 'user'|'assistant'|'tool', content, timestamp, tool_calls?, message_type?, files?, tool_call_id? }`
- `ToolCall`
  - `{ id?, name, args, status?: 'calling'|'completed'|'error', result? }`
- `SubAgentMessage`：子智能体事件的统一结构
- `StreamMessage`：SSE `message` 事件载荷结构
- `UpdateMessage`：SSE `update` 事件结构

---

## 前端 API 客户端
文件：`v2/frontend/src/api.ts`
- `getThreads()` -> `ThreadInfo[]`
- `createThread(title?)` -> `ThreadInfo`
- `deleteThread(threadId)` -> `void`
- `getThreadMessages(threadId)` -> `{ messages, files, thread_id }`
- `stopChat(threadId)` -> `void`
- `streamChat(threadId, message, onEvent, onError, onComplete)` -> `() => void`
  - 基于 `fetch` + `ReadableStream` 解析 SSE：累计字符串 buffer，以 `\n\n` 分割事件；提取 `data:` 行并 `JSON.parse`。

---

## 前端流处理器（SSE -> UI 语义）
文件：`v2/frontend/src/stream.ts`

`StreamProcessor` 将原始事件转为更高层的回调：
- `onMessageDelta(delta: string)`：主智能体文本的增量（以最长公共前缀计算差分）。
- `onToolCall(name, args, id?)`：当 `finish_reason == 'tool_calls'` 时，将累计的工具调用以结构化形式回调。
- `onToolMessage(toolCallId, result)`：当收到 `type == 'tool'` 的 `message`，根据 `additional_kwargs.tool_call_id` 将工具结果绑定到对应的工具调用上并标记完成。
- `onToolCallsComplete()`：有新工具调用产生后触发一个完成信号（用于 UI 阶段性收束）。
- `onFilesUpdate(files)`：`update` 事件中包含 `files` 时触发。
- `onSubAgentEvent(event)`：透传子智能体事件到工作区。
- `onStop()` / `onError()` / `onComplete()`：流结束、中断、错误。

工具调用的聚合逻辑：
- 流式收集 `tool_call_chunks`（name/args 分片）与 `tool_calls`（完整项）。
- 当 `finish_reason == 'tool_calls'`：
  - 按 index 合并工具调用，过滤 `write_file` 的参数展示为 `...`。
  - 去重（name|args 签名）后，通过 `onToolCall` 推出到 UI。
  - 清空本地缓冲，触发 `onToolCallsComplete()`。

---

## UI 层展示与消息分类

### 主对话（左中区域）
文件：`v2/frontend/src/components/ChatPanel.tsx`
- 仅展示 `role !== 'tool'` 的消息（工具结果不作为独立主消息显示，而是填入工具卡片内）。
- `files_update` 类型的提示以系统气泡形式展示（由 `onFilesUpdate` 注入一条 `assistant` 消息，`message_type: 'files_update'`）。
- 工具调用区块：在 `assistant` 消息下方可折叠展示每个工具调用（状态：执行中/完成/错误；参数：`write_file` 隐藏；结果：截断显示）。
- “每个消息结束都要重新提一个对话框”的实现要点：
  - 当工具阶段结束（`finish_reason == 'tool_calls'`）后，UI 仍在同一个 `assistant` 消息内显示“工具调用”卡片。
  - 当随后开始输出新的文本内容（`onMessageDelta` 触发，且上一条 `assistant` 消息已有工具卡片但正文仍为空），会新建一个新的 `assistant` 气泡用于承载新的回答段落，避免工具卡片和新文本混在同一气泡内。

简化的关键逻辑（已实现）：
```tsx
onMessageDelta: (delta) => {
  setMessages(prev => {
    const updated = [...prev];
    const last = updated[updated.length - 1];
    if (!last || last.role !== 'assistant') {
      updated.push({ role: 'assistant', content: delta, timestamp: now(), tool_calls: [] });
    } else if (last.tool_calls?.length && !last.content.trim() && delta.trim()) {
      // 上一条是工具块，且还没有正文，这时开启新气泡
      updated.push({ role: 'assistant', content: delta, timestamp: now(), tool_calls: [] });
    } else {
      last.content += delta;
    }
    return updated;
  });
}
```

### 子智能体（右侧工作区）
文件：`v2/frontend/src/components/WorkspacePanel.tsx`
- 子智能体事件通过 `onSubAgentEvent` 汇总，集中展示在“子智能体输出”区域：
  - `start`：显示启动与任务描述
  - `chunk/messages`：按 agent 维度进行流式聚合，生成/更新同一条消息
  - `tool_call`：以小工具卡形式折叠展示
  - `updates(files)`：文件更新会触发工作区文件树刷新，并追加一条“文件更新”消息
  - `stop`：输出“任务完成”消息
- 子智能体与主智能体消息严格分离显示，不进入主对话。

### 文件工作区
- `update` 事件或子智能体文件更新时，更新 `files: Record<string, string[]>` 并展示文件摘要；文件内容可折叠查看，预览最多若干行。

---

## 典型时序与生命周期

1) 用户发送消息：
- 前端立即插入一条 `user` 消息与一个空壳 `assistant` 消息（用于承接流）。
- 调用 `/api/chat/stream` 开启 SSE。

2) 主智能体响应阶段：
- 持续收到 `message` 事件的文本增量，填充当前 `assistant` 消息。
- 当模型决定调用工具：
  - `message` 事件的 `finish_reason = 'tool_calls'`，前端合并并展示“工具调用卡片”。
  - 随后可能收到 `type = 'tool'` 的 `message`（工具返回结果），前端将结果回填到相应卡片并标记完成。
  - 紧随其后如果继续产生新的文本内容，将新开一个 `assistant` 气泡承载。

3) 文件更新：
- 任意时刻收到 `update` 携带 `files`，工作区更新；主对话插入一条 `files_update` 系统消息。

4) 子智能体：
- `subagent` 事件仅进入右侧工作区，以更细粒度展示其流式过程、工具调用与文件更新。

5) 结束/中断：
- 正常完成：`finish_reason = 'stop'` 或流读尽，触发 `onComplete`，`isStreaming=false`，刷新 Thread 列表。
- 主动停止：发 `/api/chat/stop`，收到 `stop` 事件，触发 `onStop`，并释放 reader。

---

## 已知问题与改进建议（Bugs & TODO）

- 线程消息数 `message_count` 未更新：
  - 目前恒为 `0`。建议在后端 `get_thread_messages` 统计或在 LangGraph 写入后更新。

- 前端未传 `user_id`：
  - 后端默认 `x_lab`。如后续需要多用户，请在前端 API 加上 `user_id` 透传，并在后端校验。

- SSE 事件头未利用：
  - 目前前端仅解析 `data:` 的 JSON，不使用 `event:`。虽然可用，但严格实现可根据 `event:` 做分发，健壮性更好。

- 工具消息 `tool_message` 的 `tool_call_id` 依赖上游：
  - `StreamProcessor` 通过 `additional_kwargs.tool_call_id` 关联结果与工具调用。若上游模型未提供该字段，可能无法正确回填。建议在后端做一次兜底匹配（基于最近的调用顺序）。

- 工具参数隐私过滤：
  - 后端已针对 `write_file` 将参数替换为 `...`。如还有其它敏感工具，需加入 `UI_VISIBILITY.hide_tool_calls_for` 白名单。

- 子智能体消息在主对话中不出现：
  - 设计如此（分区显示）。如需要主对话中插入“子智能体阶段提示”，可在后端增加一条 `message_type=subagent_state` 的 `assistant` 系统消息提示。

- 并发与可重入：
  - 同线程多流返回 `409`。前端在切换线程或开始新流时，务必调用停止函数与重置 `StreamProcessor`（已实现）。

---

## 参考实现要点（函数/接口）

- 后端 SSE 格式化（已实现）：
```python
# app.py
json_data = json.dumps({"type": event_type, "data": data}, ensure_ascii=False, default=str)
return f"event: {event_type}\ndata: {json_data}\n\n"
```

- 前端工具调用聚合（已实现）：
```ts
// stream.ts（节选）
if (finishReason === 'tool_calls') {
  // 合并分片与完整项 -> onToolCall
  this.handlers.onToolCallsComplete?.();
} else if (finishReason === 'stop') {
  this.handlers.onComplete?.();
}
```

- 前端“工具 -> 结果 -> 新气泡”分段（已实现）：见 ChatPanel 中 `onMessageDelta` 逻辑与 `onToolMessage` 回填。

---

## 快速使用
1) 启动后端（建议在 `v2/server` 下）：
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```
2) 启动前端（在 `v2/frontend` 下）：
```bash
npm install
npm run dev
```
3) 打开前端 UI：创建新对话，发送消息，观察主对话与工作区的分工显示。

---

如需扩展事件类型或消息分类，请保持：
- 主/子智能体消息严格分区；
- 工具调用与工具返回在同一块 UI 内闭环；
- 每个阶段（工具阶段结束、文本阶段结束）以新气泡承载，保证可读性。
