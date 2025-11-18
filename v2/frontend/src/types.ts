export interface ChatMessage {
  role: 'user' | 'assistant' | 'tool';
  content: string;
  timestamp: string;
  tool_calls?: ToolCall[];
  message_type?: string;
  files?: Record<string, string[]>;
  tool_call_id?: string; // For tool messages to reference the original tool call
}

export interface ToolCall {
  id?: string; // Unique identifier for the tool call
  name: string;
  args: string;
  status?: 'calling' | 'completed' | 'error'; // Tool call status
  result?: string; // Tool call result from tool_message
}

export interface ThreadInfo {
  thread_id: string;
  title: string;
  created_at: string;
  last_message_at?: string;
  message_count: number;
}

export interface FileInfo {
  path: string;
  content: string[];
}

export interface SubAgentMessage {
  type: 'start' | 'stop' | 'chunk' | 'content' | 'tool_call' | 'message' | 'files_update';
  name?: string;
  description?: string;
  text?: string;
  stream_type?: string;
  data?: any;
  tool_calls?: ToolCall[];
  files?: Record<string, string[]>;
  role?: 'user' | 'assistant' | 'tool';
  timestamp?: string;
}

export interface StreamMessage {
  content: string;
  type: string;
  additional_kwargs: {
    tool_call_chunks?: Array<{
      index: number;
      name?: string;
      args?: string;
    }>;
    tool_calls?: Array<{
      index: number;
      function?: {
        name: string;
        arguments: string;
      };
      name?: string;
      args?: string;
    }>;
  };
  response_metadata: {
    finish_reason?: string;
  };
}

export interface UpdateMessage {
  [nodeKey: string]: {
    files?: Record<string, string[]>;
    todos?: Array<{
      content: string;
      status: 'pending' | 'in_progress' | 'completed';
    }>;
  };
}