import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Square, User, Bot, Wrench, ChevronDown, ChevronRight } from 'lucide-react';
import { ChatMessage, ToolCall } from '../types';

interface ChatPanelProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  onSendMessage: (message: string) => void;
  onStopStreaming: () => void;
  activeThreadId: string | null;
}

interface MessageComponentProps {
  message: ChatMessage;
  isStreaming?: boolean;
}

const MessageComponent: React.FC<MessageComponentProps> = ({ message, isStreaming }) => {
  const [toolCallsExpanded, setToolCallsExpanded] = useState(false);

  const renderAvatar = () => {
    if (message.role === 'user') {
      return (
        <div className="message-avatar">
          <User size={16} />
        </div>
      );
    } else if (message.role === 'assistant') {
      return (
        <div className="message-avatar">
          <Bot size={16} />
        </div>
      );
    } else if (message.role === 'tool') {
      return (
        <div className="message-avatar" style={{ backgroundColor: 'var(--tool-bg)' }}>
          <Wrench size={16} />
        </div>
      );
    }
    return null;
  };

  const renderFilesUpdate = (files: Record<string, string[]>) => {
    if (!files || Object.keys(files).length === 0) return null;

    return (
      <div className="files-update-container">
        <div className="files-update-header">
          📁 工作区文件已更新
        </div>
        {Object.entries(files).map(([filePath, content]) => (
          <div key={filePath} className="file-update-item">
            <div className="file-path">{filePath}</div>
            <div className="file-content-preview">
              {content.slice(0, 5).map((line, index) => (
                <div key={index} className="file-line">
                  <span className="line-number">{index + 1}</span>
                  <span className="line-content">{line}</span>
                </div>
              ))}
              {content.length > 5 && (
                <div className="file-line-more">... 共 {content.length} 行</div>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderToolCalls = (toolCalls: ToolCall[]) => {
    if (!toolCalls || toolCalls.length === 0) return null;

    return (
      <div className="tool-calls">
        <div 
          className="tool-calls-header"
          onClick={() => setToolCallsExpanded(!toolCallsExpanded)}
          style={{ 
            cursor: 'pointer', 
            display: 'flex', 
            alignItems: 'center',
            fontSize: '0.8rem',
            fontWeight: '600',
            marginBottom: toolCallsExpanded ? '0.5rem' : '0'
          }}
        >
          {toolCallsExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <span style={{ marginLeft: '0.25rem' }}>
            工具调用 ({toolCalls.length} 个)
          </span>
        </div>
        
        {toolCallsExpanded && (
          <div className="tool-calls-content">
            {toolCalls.map((toolCall, index) => (
              <div key={toolCall.id || index} className="tool-call-item">
                <div className="tool-call-header">
                  <span className="tool-name">{toolCall.name}</span>
                  <span className={`tool-status ${toolCall.status || 'calling'}`}>
                    {toolCall.status === 'completed' ? '✅ 完成' : 
                     toolCall.status === 'error' ? '❌ 错误' : 
                     '⏳ 执行中...'}
                  </span>
                </div>
                
                {/* 显示参数（除了write_file） */}
                {toolCall.args && toolCall.name !== 'write_file' && (
                  <div className="tool-args">
                    <strong>参数:</strong>
                    <pre>{toolCall.args}</pre>
                  </div>
                )}
                
                {/* 显示结果 */}
                {toolCall.result && toolCall.status === 'completed' && (
                  <div className="tool-result">
                    <strong>结果:</strong>
                    <div className="tool-result-content">
                      {toolCall.result.length > 200 
                        ? `${toolCall.result.substring(0, 200)}...` 
                        : toolCall.result}
                    </div>
                  </div>
                )}
                
                {/* Task工具的特殊处理（子智能体调用） */}
                {toolCall.name === 'task' && (
                  <div className="task-info">
                    <div>📋 子智能体任务已启动</div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      详细输出请查看右侧工作区
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={`message ${message.role}`}>
      {renderAvatar()}
      <div className="message-bubble">
        {message.message_type === 'files_update' ? (
          renderFilesUpdate(message.files || {})
        ) : (
          <>
            <div className="message-content">
              <ReactMarkdown>{message.content}</ReactMarkdown>
              {isStreaming && message.role === 'assistant' && (
                <span className="cursor">|</span>
              )}
            </div>
            {message.tool_calls && renderToolCalls(message.tool_calls)}
          </>
        )}
      </div>
    </div>
  );
};

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  isStreaming,
  onSendMessage,
  onStopStreaming,
  activeThreadId,
}) => {
  const [inputText, setInputText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (!inputText.trim() || isStreaming || !activeThreadId) return;
    
    onSendMessage(inputText.trim());
    setInputText('');
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
    
    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 128) + 'px';
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h1>DeepAgent XLanguage</h1>
        {activeThreadId && (
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Thread: {activeThreadId.slice(0, 8)}...
          </div>
        )}
      </div>
      
      <div className="messages-container">
        {!activeThreadId ? (
          <div className="empty-chat">
            <div style={{ 
              textAlign: 'center', 
              color: 'var(--text-muted)',
              marginTop: '2rem'
            }}>
              <Bot size={64} style={{ marginBottom: '1rem' }} />
              <h2>欢迎使用 DeepAgent XLanguage</h2>
              <p>选择一个对话或创建新对话开始</p>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="empty-chat">
            <div style={{ 
              textAlign: 'center', 
              color: 'var(--text-muted)',
              marginTop: '2rem'
            }}>
              <p>开始新的对话</p>
            </div>
          </div>
        ) : (
          messages.filter(msg => msg.role !== 'tool').map((message, index) => (
            <MessageComponent
              key={index}
              message={message}
              isStreaming={isStreaming && index === messages.filter(msg => msg.role !== 'tool').length - 1}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="input-area">
        <div className="input-container">
          <textarea
            ref={textareaRef}
            className="message-input"
            placeholder={
              !activeThreadId 
                ? "请先选择或创建一个对话" 
                : isStreaming 
                  ? "正在处理中..." 
                  : "输入消息..."
            }
            value={inputText}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            disabled={!activeThreadId || isStreaming}
            rows={1}
          />
          
          {isStreaming ? (
            <button 
              className="stop-btn" 
              onClick={onStopStreaming}
              title="停止生成"
            >
              <Square size={16} />
            </button>
          ) : (
            <button
              className="send-btn"
              onClick={handleSend}
              disabled={!inputText.trim() || !activeThreadId}
              title="发送消息"
            >
              <Send size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};