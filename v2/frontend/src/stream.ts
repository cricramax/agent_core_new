import { StreamMessage, UpdateMessage, SubAgentMessage } from './types';

export interface StreamHandlers {
  onMessageDelta?: (delta: string) => void;
  onToolCall?: (name: string, args: string, toolCallId?: string) => void;
  onToolMessage?: (toolCallId: string, result: string) => void;
  onToolCallsComplete?: () => void;
  onFilesUpdate?: (files: Record<string, string[]>) => void;
  onSubAgentEvent?: (event: import('./types').SubAgentMessage) => void;
  onStop?: () => void;
  onError?: (error: any) => void;
  onComplete?: () => void;
}

export class StreamProcessor {
  private handlers: StreamHandlers;
  private bufferedText = '';
  private toolCallChunks: Record<number, { name: string | null; args: string; id?: string }> = {};
  private printedToolCalls = new Set<string>();

  constructor(handlers: StreamHandlers) {
    this.handlers = handlers;
  }

  processEvent(eventData: any) {
    const { type, data } = eventData;

    switch (type) {
      case 'message':
        this.handleMessage(data);
        break;
      case 'update':
        this.handleUpdate(data);
        break;
      case 'subagent':
        this.handleSubAgent(data);
        break;
      case 'stop':
        this.handlers.onStop?.();
        break;
      case 'error':
        this.handlers.onError?.(data);
        break;
      default:
        console.log('Unknown event type:', type, data);
    }
  }

  private handleMessage(message: StreamMessage) {
    // Check if this is a tool message (tool call result)
    if (message.type === 'tool') {
      const toolCallId = message.additional_kwargs?.tool_call_id;
      const result = message.content || '';
      if (toolCallId) {
        this.handlers.onToolMessage?.(toolCallId, result);
      }
      return;
    }

    // Handle text content delta for assistant messages
    const content = message.content || '';
    const delta = this.calculateDelta(this.bufferedText, content);
    if (delta) {
      this.handlers.onMessageDelta?.(delta);
    }
    this.bufferedText = content;

    // Handle tool call chunks (流式输出)
    const addKw = message.additional_kwargs || {};
    
    // Process tool_call_chunks
    for (const chunk of addKw.tool_call_chunks || []) {
      const idx = chunk.index || 0;
      if (!this.toolCallChunks[idx]) {
        this.toolCallChunks[idx] = { name: null, args: '', id: chunk.id };
      }
      const buf = this.toolCallChunks[idx];
      if (chunk.name) buf.name = chunk.name;
      if (chunk.args) buf.args += chunk.args;
      if (chunk.id) buf.id = chunk.id;
    }

    // Process tool_calls
    for (const tc of addKw.tool_calls || []) {
      const idx = tc.index || 0;
      const func = tc.function as any || {};
      const name = func?.name || tc?.name || '';
      const args = func?.arguments || tc?.args || '';
      
      if (!this.toolCallChunks[idx]) {
        this.toolCallChunks[idx] = { name: null, args: '', id: tc.id };
      }
      const buf = this.toolCallChunks[idx];
      if (name) buf.name = name;
      if (args) buf.args += args;
      if (tc.id) buf.id = tc.id;
    }

    // Check if tool calls are complete
    const finishReason = message.response_metadata?.finish_reason;
    if (finishReason === 'tool_calls') {
      const indices = Object.keys(this.toolCallChunks).map(Number).sort();
      let hasNewToolCalls = false;
      for (const idx of indices) {
        const buf = this.toolCallChunks[idx];
        if (buf?.name && buf.args) {
          // Filter write_file arguments
          const displayArgs = buf.name === 'write_file' ? '...' : buf.args;
          const signature = `${buf.name}|${buf.args}`;
          if (!this.printedToolCalls.has(signature)) {
            this.handlers.onToolCall?.(buf.name, displayArgs, buf.id);
            this.printedToolCalls.add(signature);
            hasNewToolCalls = true;
          }
        }
      }
      this.toolCallChunks = {};
      
      // 通知工具调用完成
      if (hasNewToolCalls) {
        this.handlers.onToolCallsComplete?.();
      }
    } else if (finishReason === 'stop') {
      this.handlers.onComplete?.();
    }
  }

  private handleUpdate(update: UpdateMessage) {
    for (const nodeData of Object.values(update)) {
      if (nodeData.files) {
        this.handlers.onFilesUpdate?.(nodeData.files);
      }
    }
  }

  private handleSubAgent(event: SubAgentMessage) {
    // 简单直接地转发所有子智能体事件到工作区
    this.handlers.onSubAgentEvent?.(event);
  }

  private calculateDelta(previous: string, current: string): string {
    // Find longest common prefix
    const maxLength = Math.min(previous.length, current.length);
    let commonLength = 0;
    
    while (commonLength < maxLength && previous[commonLength] === current[commonLength]) {
      commonLength++;
    }
    
    return current.slice(commonLength);
  }

  reset() {
    this.bufferedText = '';
    this.toolCallChunks = {};
    this.printedToolCalls.clear();
  }
}