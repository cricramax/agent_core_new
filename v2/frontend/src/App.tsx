import { useState, useEffect, useRef } from 'react';
import { HistoryPanel } from './components/HistoryPanel';
import { ChatPanel } from './components/ChatPanel';
import { WorkspacePanel } from './components/WorkspacePanel';
import { ApiClient } from './api';
import { StreamProcessor, StreamHandlers } from './stream';
import { ThreadInfo, ChatMessage, SubAgentMessage, ToolCall } from './types';

function App() {
  // State management
  const [threads, setThreads] = useState<ThreadInfo[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [files, setFiles] = useState<Record<string, string[]>>({});
  // const [subAgentFiles, setSubAgentFiles] = useState<Record<string, Record<string, string[]>>>({});
  const [subAgentMessages, setSubAgentMessages] = useState<SubAgentMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [workspaceCollapsed, setWorkspaceCollapsed] = useState(false);

  // Refs for streaming
  const stopStreamRef = useRef<(() => void) | null>(null);
  const streamProcessorRef = useRef<StreamProcessor | null>(null);

  // Load threads on component mount
  useEffect(() => {
    loadThreads();
  }, []);

  // Load messages when active thread changes
  useEffect(() => {
    if (activeThreadId) {
      loadThreadMessages(activeThreadId);
    } else {
      setMessages([]);
      setFiles({});
      setSubAgentMessages([]);
    }
  }, [activeThreadId]);

  const loadThreads = async () => {
    try {
      setIsLoading(true);
      const threadsData = await ApiClient.getThreads();
      setThreads(threadsData);
    } catch (error) {
      console.error('Failed to load threads:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadThreadMessages = async (threadId: string) => {
    try {
      const { messages: threadMessages, files: threadFiles } = await ApiClient.getThreadMessages(threadId);
      setMessages(threadMessages);
      setFiles(threadFiles);
      setSubAgentMessages([]); // Reset sub-agent messages for new thread
    } catch (error) {
      console.error('Failed to load thread messages:', error);
      setMessages([]);
      setFiles({});
      setSubAgentMessages([]);
    }
  };

  const handleCreateThread = async () => {
    try {
      const newThread = await ApiClient.createThread();
      setThreads([newThread, ...threads]);
      setActiveThreadId(newThread.thread_id);
    } catch (error) {
      console.error('Failed to create thread:', error);
    }
  };

  const handleSelectThread = (threadId: string) => {
    if (isStreaming) {
      // Stop current stream if switching threads
      handleStopStreaming();
    }
    setActiveThreadId(threadId);
  };

  const handleSendMessage = async (message: string) => {
    if (!activeThreadId || isStreaming) return;

    // Add user message immediately
    const userMessage: ChatMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    // Prepare assistant message placeholder
    const assistantMessage: ChatMessage = {
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      tool_calls: [],
    };
    setMessages(prev => [...prev, assistantMessage]);

    // Set up streaming
    setIsStreaming(true);
    
    try {
      // Create stream processor
      const streamHandlers: StreamHandlers = {
        onMessageDelta: (delta: string) => {
          setMessages(prev => {
            const updated = [...prev];
            let lastMessage = updated[updated.length - 1];
            
            // If the last message is not an assistant message or it has tool_calls but no content yet,
            // and we're getting new content, we might need to create a new message block
            if (!lastMessage || lastMessage.role !== 'assistant') {
              // This shouldn't happen in normal flow, but handle it gracefully
              const newMessage: ChatMessage = {
                role: 'assistant',
                content: delta,
                timestamp: new Date().toISOString(),
                tool_calls: [],
              };
              updated.push(newMessage);
            } else if (lastMessage.tool_calls && lastMessage.tool_calls.length > 0 && !lastMessage.content.trim() && delta.trim()) {
              // If the last message has tool calls but no content, and we're getting new content,
              // this might be a new response block after tool execution
              const newMessage: ChatMessage = {
                role: 'assistant',
                content: delta,
                timestamp: new Date().toISOString(),
                tool_calls: [],
              };
              updated.push(newMessage);
            } else {
              // Normal case: append to existing message
              lastMessage.content += delta;
            }
            
            return updated;
          });
        },

        onToolCall: (name: string, args: string, toolCallId?: string) => {
          const toolCall: ToolCall = { 
            name, 
            args, 
            id: toolCallId,
            status: 'calling' 
          };
          setMessages(prev => {
            const updated = [...prev];
            const lastMessage = updated[updated.length - 1];
            if (lastMessage && lastMessage.role === 'assistant') {
              if (!lastMessage.tool_calls) {
                lastMessage.tool_calls = [];
              }
              // 检查是否已经存在相同的工具调用，避免重复
              const exists = lastMessage.tool_calls.some(tc => 
                tc.name === toolCall.name && tc.args === toolCall.args
              );
              if (!exists) {
                lastMessage.tool_calls.push(toolCall);
              }
            }
            return updated;
          });
        },

        onToolMessage: (toolCallId: string, result: string) => {
          setMessages(prev => {
            const updated = [...prev];
            // Find the tool call with this ID and update its status
            for (let i = updated.length - 1; i >= 0; i--) {
              const msg = updated[i];
              if (msg.role === 'assistant' && msg.tool_calls) {
                for (const toolCall of msg.tool_calls) {
                  if (toolCall.id === toolCallId) {
                    toolCall.status = 'completed';
                    toolCall.result = result;
                    return updated;
                  }
                }
              }
            }
            return updated;
          });
        },

        onToolCallsComplete: () => {
          // 工具调用完成，准备接收新的消息内容
        },

        onFilesUpdate: (newFiles: Record<string, string[]>) => {
          setFiles(newFiles);
          
          // Create a files update message in the chat
          const filesUpdateMessage: ChatMessage = {
            role: 'assistant',
            content: '', // No text content for files update
            timestamp: new Date().toISOString(),
            message_type: 'files_update',
            files: newFiles
          };
          
          setMessages(prev => [...prev, filesUpdateMessage]);
        },

        onSubAgentEvent: (event: SubAgentMessage) => {
          // 子智能体事件只传递给WorkspacePanel，不影响主对话框
          setSubAgentMessages(prev => [...prev, event]);
        },

        onStop: () => {
          setIsStreaming(false);
        },

        onError: (error: any) => {
          console.error('Stream error:', error);
          setIsStreaming(false);
        },

        onComplete: () => {
          setIsStreaming(false);
          // Refresh thread list to update message counts
          loadThreads();
        },
      };

      const processor = new StreamProcessor(streamHandlers);
      streamProcessorRef.current = processor;

      // Start streaming
      const stopFn = await ApiClient.streamChat(
        activeThreadId,
        message,
        (data) => processor.processEvent(data),
        (error) => {
          console.error('Stream error:', error);
          setIsStreaming(false);
        },
        () => {
          setIsStreaming(false);
          loadThreads();
        }
      );
      
      stopStreamRef.current = stopFn;

    } catch (error) {
      console.error('Failed to start streaming:', error);
      setIsStreaming(false);
    }
  };

  const handleStopStreaming = async () => {
    if (!activeThreadId) return;

    try {
      await ApiClient.stopChat(activeThreadId);
    } catch (error) {
      console.error('Failed to stop chat:', error);
    }

    // Clean up streaming resources
    if (stopStreamRef.current) {
      stopStreamRef.current();
      stopStreamRef.current = null;
    }

    if (streamProcessorRef.current) {
      streamProcessorRef.current.reset();
      streamProcessorRef.current = null;
    }

    setIsStreaming(false);
  };

  const handleClearSubAgentMessages = () => {
    setSubAgentMessages([]);
  };

  const handleFilesUpdate = (newFiles: Record<string, string[]>) => {
    setFiles(prev => ({ ...prev, ...newFiles }));
  };

  const handleToggleWorkspace = () => {
    setWorkspaceCollapsed(!workspaceCollapsed);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (stopStreamRef.current) {
        stopStreamRef.current();
      }
    };
  }, []);

  return (
    <div className={`app ${workspaceCollapsed ? 'workspace-collapsed' : ''}`}>
      <HistoryPanel
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={handleSelectThread}
        onCreateThread={handleCreateThread}
        isLoading={isLoading}
      />
      
      <ChatPanel
        messages={messages}
        isStreaming={isStreaming}
        onSendMessage={handleSendMessage}
        onStopStreaming={handleStopStreaming}
        activeThreadId={activeThreadId}
      />
      
      <WorkspacePanel
        files={files}
        subAgentMessages={subAgentMessages}
        onClearSubAgentMessages={handleClearSubAgentMessages}
        onFilesUpdate={handleFilesUpdate}
        collapsed={workspaceCollapsed}
        onToggleCollapse={handleToggleWorkspace}
      />
    </div>
  );
}

export default App;