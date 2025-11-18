import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { File, Folder, ChevronDown, ChevronRight, Activity, X, User, Bot, Wrench, ChevronLeft } from 'lucide-react';
import { SubAgentMessage, ToolCall } from '../types';

interface WorkspacePanelProps {
  files: Record<string, string[]>;
  subAgentMessages: SubAgentMessage[];
  onClearSubAgentMessages: () => void;
  onFilesUpdate: (files: Record<string, string[]>) => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

interface FileItemProps {
  path: string;
  content: string[];
}

const FileItem: React.FC<FileItemProps> = ({ path, content }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="file-item">
      <div 
        className="file-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <File size={14} style={{ marginRight: '0.5rem' }} />
          <span className="file-path">{path}</span>
        </div>
        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </div>
      
      {isExpanded && (
        <div className="file-content">
          {content.map((line, index) => (
            <div key={index} style={{ marginBottom: '0.25rem' }}>
              <span style={{ 
                color: 'var(--text-muted)', 
                marginRight: '1rem',
                minWidth: '2rem',
                display: 'inline-block'
              }}>
                {index + 1}
              </span>
              {line}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

interface SubAgentMessageComponentProps {
  message: SubAgentMessage;
}

const SubAgentMessageComponent: React.FC<SubAgentMessageComponentProps> = ({ message }) => {
  const [toolCallsExpanded, setToolCallsExpanded] = useState(false);

  const renderAvatar = () => {
    if (message.role === 'user') {
      return (
        <div className="message-avatar">
          <User size={12} />
        </div>
      );
    } else if (message.role === 'assistant') {
      return (
        <div className="message-avatar">
          <Bot size={12} />
        </div>
      );
    } else if (message.role === 'tool') {
      return (
        <div className="message-avatar" style={{ backgroundColor: 'var(--tool-bg)' }}>
          <Wrench size={12} />
        </div>
      );
    }
    return null;
  };

  const renderToolCalls = (toolCalls: ToolCall[]) => {
    if (!toolCalls || toolCalls.length === 0) return null;

    return (
      <div className="tool-calls" style={{ fontSize: '0.7rem', marginTop: '0.25rem' }}>
        <div 
          className="tool-calls-header"
          onClick={() => setToolCallsExpanded(!toolCallsExpanded)}
          style={{ 
            cursor: 'pointer', 
            display: 'flex', 
            alignItems: 'center',
            fontSize: '0.7rem',
            fontWeight: '600',
            marginBottom: toolCallsExpanded ? '0.25rem' : '0'
          }}
        >
          {toolCallsExpanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
          <span style={{ marginLeft: '0.25rem' }}>
            工具调用 ({toolCalls.length} 个)
          </span>
        </div>
        
        {toolCallsExpanded && (
          <div className="tool-calls-content">
            {toolCalls.map((toolCall, index) => (
              <div key={toolCall.id || index} className="tool-call-item" style={{ marginBottom: '0.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="tool-name" style={{ fontSize: '0.7rem', fontWeight: '600' }}>
                    {toolCall.name}
                  </span>
                  <span className={`tool-status ${toolCall.status || 'calling'}`} style={{ fontSize: '0.6rem' }}>
                    {toolCall.status === 'completed' ? '✅' : 
                     toolCall.status === 'error' ? '❌' : 
                     '⏳'}
                  </span>
                </div>
                
                {toolCall.args && toolCall.name !== 'write_file' && (
                  <div style={{ 
                    marginTop: '0.125rem', 
                    fontSize: '0.6rem',
                    fontFamily: 'monospace',
                    color: 'var(--text-muted)',
                    paddingLeft: '0.5rem',
                    whiteSpace: 'pre-wrap'
                  }}>
                    {toolCall.args}
                  </div>
                )}
                
                {toolCall.result && toolCall.status === 'completed' && (
                  <div style={{ 
                    marginTop: '0.125rem', 
                    fontSize: '0.6rem',
                    color: 'var(--text-success)',
                    paddingLeft: '0.5rem'
                  }}>
                    结果: {toolCall.result.length > 100 ? `${toolCall.result.substring(0, 100)}...` : toolCall.result}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  const renderFilesUpdate = (files: Record<string, string[]>) => {
    if (!files || Object.keys(files).length === 0) return null;

    return (
      <div style={{
        background: 'var(--bg-secondary)',
        padding: '0.5rem',
        borderRadius: '0.5rem',
        marginTop: '0.25rem'
      }}>
        <div style={{ fontSize: '0.7rem', fontWeight: '600', marginBottom: '0.25rem' }}>
          📁 文件更新
        </div>
        {Object.entries(files).slice(0, 3).map(([filePath, content]) => (
          <div key={filePath} style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>
            {filePath}
          </div>
        ))}
        {Object.keys(files).length > 3 && (
          <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>
            ... 共 {Object.keys(files).length} 个文件
          </div>
        )}
      </div>
    );
  };

  // 处理不同类型的消息
  if (message.type === 'files_update') {
    return (
      <div className="subagent-message-item" style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.5rem',
        marginBottom: '0.5rem',
        fontSize: '0.75rem'
      }}>
        <div className="message-avatar" style={{ backgroundColor: 'var(--accent)' }}>
          <File size={12} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          {renderFilesUpdate(message.files || {})}
        </div>
      </div>
    );
  }

  if (message.type === 'message' || !message.type) {
    return (
      <div className="subagent-message-item" style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.5rem',
        marginBottom: '0.5rem',
        fontSize: '0.75rem'
      }}>
        {renderAvatar()}
        <div style={{ flex: 1, minWidth: 0 }}>
          {message.text && (
            <div style={{
              background: 'var(--bg-primary)',
              padding: '0.5rem',
              borderRadius: '0.5rem',
              marginBottom: '0.25rem'
            }}>
              <ReactMarkdown>{message.text}</ReactMarkdown>
            </div>
          )}
          {message.tool_calls && renderToolCalls(message.tool_calls)}
        </div>
      </div>
    );
  }

  return null;
};

interface SubAgentFeedProps {
  messages: SubAgentMessage[];
  onClear: () => void;
  onFilesUpdate: (files: Record<string, string[]>) => void;
}

const SubAgentFeed: React.FC<SubAgentFeedProps> = ({ messages, onClear, onFilesUpdate }) => {
  const [processedMessages, setProcessedMessages] = useState<SubAgentMessage[]>([]);

  useEffect(() => {
    // 处理原始的子智能体消息，实现流式输出合并
    const processed: SubAgentMessage[] = [];
    const activeAgents: Record<string, { 
      content: string; 
      toolCalls: ToolCall[];
      lastMessageIndex?: number;
    }> = {};

    for (const msg of messages) {
      const agentName = msg.name || 'subagent';
      
      if (msg.type === 'start') {
        // 子智能体启动
        processed.push({
          ...msg,
          type: 'message',
          text: `🚀 启动子智能体: ${agentName}${msg.description ? `\n📝 任务描述: ${msg.description}` : ''}`,
          role: 'assistant',
          timestamp: new Date().toISOString()
        });
        
        // 初始化或重置智能体状态
        activeAgents[agentName] = {
          content: '',
          toolCalls: []
        };
        
      } else if (msg.type === 'stop') {
        // 子智能体结束，输出最终内容
        const agent = activeAgents[agentName];
        if (agent) {
          // 如果有累积的内容或工具调用，创建消息
          if (agent.content.trim() || agent.toolCalls.length > 0) {
            processed.push({
              type: 'message',
              name: agentName,
              text: agent.content,
              role: 'assistant',
              tool_calls: agent.toolCalls.length > 0 ? agent.toolCalls : undefined,
              timestamp: new Date().toISOString()
            });
          }
          
          // 删除智能体状态
          delete activeAgents[agentName];
        }
        
        // 添加完成消息
        processed.push({
          type: 'message',
          name: agentName,
          text: '✅ 子智能体任务完成',
          role: 'assistant',
          timestamp: new Date().toISOString()
        });
        
      } else if (msg.type === 'chunk' && msg.stream_type === 'messages' && msg.data) {
        // 处理消息chunk - 流式合并
        const [messageChunk] = msg.data;
        if (!activeAgents[agentName]) {
          activeAgents[agentName] = { content: '', toolCalls: [] };
        }
        
        const agent = activeAgents[agentName];
        const content = messageChunk?.content || '';
        
        // 累积文本内容
        if (content) {
          agent.content += content;
        }
        
        // 处理工具调用
        const addKw = messageChunk?.additional_kwargs || {};
        const toolCalls = addKw.tool_calls || [];
        if (toolCalls.length > 0) {
          for (const tc of toolCalls) {
            const toolCall: ToolCall = {
              id: tc.id || tc.index?.toString(),
              name: tc.function?.name || tc.name || '',
              args: tc.function?.arguments || tc.args || '',
              status: 'calling'
            };
            
            // 检查是否已存在相同的工具调用
            const exists = agent.toolCalls.find(existing => 
              existing.id === toolCall.id || 
              (existing.name === toolCall.name && existing.args === toolCall.args)
            );
            
            if (!exists) {
              agent.toolCalls.push(toolCall);
            }
          }
        }
        
        // 更新或创建最新的处理中消息
        if (agent.lastMessageIndex !== undefined) {
          // 更新现有消息
          processed[agent.lastMessageIndex] = {
            type: 'message',
            name: agentName,
            text: agent.content,
            role: 'assistant',
            tool_calls: agent.toolCalls.length > 0 ? [...agent.toolCalls] : undefined,
            timestamp: new Date().toISOString()
          };
        } else if (agent.content.trim() || agent.toolCalls.length > 0) {
          // 创建新消息
          agent.lastMessageIndex = processed.length;
          processed.push({
            type: 'message',
            name: agentName,
            text: agent.content,
            role: 'assistant',
            tool_calls: agent.toolCalls.length > 0 ? [...agent.toolCalls] : undefined,
            timestamp: new Date().toISOString()
          });
        }
        
      } else if (msg.type === 'chunk' && msg.stream_type === 'updates' && msg.data) {
        // 处理文件更新
        for (const nodeData of Object.values(msg.data)) {
          const data = nodeData as any;
          if (data.files) {
            onFilesUpdate(data.files);
            
            // 添加文件更新消息
            processed.push({
              type: 'files_update',
              name: agentName,
              text: '',
              files: data.files,
              timestamp: new Date().toISOString()
            });
          }
        }
      }
    }

    setProcessedMessages(processed);
  }, [messages, onFilesUpdate]);

  return (
    <div>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '0.75rem'
      }}>
        <div className="section-title">子智能体输出</div>
        {processedMessages.length > 0 && (
          <button
            onClick={onClear}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '0.25rem',
              borderRadius: '0.25rem',
              display: 'flex',
              alignItems: 'center'
            }}
            title="清空消息"
          >
            <X size={14} />
          </button>
        )}
      </div>
      
      <div className="subagent-feed">
        {processedMessages.length === 0 ? (
          <div style={{ 
            textAlign: 'center', 
            color: 'var(--text-muted)',
            padding: '2rem'
          }}>
            <Activity size={32} style={{ marginBottom: '0.5rem' }} />
            <p>暂无子智能体输出</p>
          </div>
        ) : (
          <div style={{ fontSize: '0.8rem' }}>
            {processedMessages.map((msg, index) => (
              <SubAgentMessageComponent key={`${msg.name}-${index}`} message={msg} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export const WorkspacePanel: React.FC<WorkspacePanelProps> = ({
  files,
  subAgentMessages,
  onClearSubAgentMessages,
  onFilesUpdate,
  collapsed = false,
  onToggleCollapse,
}) => {
  const fileEntries = Object.entries(files);

  if (collapsed) {
    return (
      <div className="workspace-panel collapsed">
        <div className="workspace-collapse-trigger" onClick={onToggleCollapse}>
          <ChevronLeft size={16} />
        </div>
      </div>
    );
  }

  return (
    <div className="workspace-panel">
      <div className="workspace-header">
        <h2>工作区</h2>
        {onToggleCollapse && (
          <button className="collapse-btn" onClick={onToggleCollapse}>
            <ChevronRight size={16} />
          </button>
        )}
      </div>
      
      <div className="workspace-content">
        {/* Files Section */}
        <div className="files-section">
          <div className="section-title">文件</div>
          {fileEntries.length === 0 ? (
            <div style={{ 
              textAlign: 'center', 
              color: 'var(--text-muted)',
              padding: '2rem'
            }}>
              <Folder size={32} style={{ marginBottom: '0.5rem' }} />
              <p>暂无文件</p>
            </div>
          ) : (
            fileEntries.map(([path, content]) => (
              <FileItem
                key={path}
                path={path}
                content={content}
              />
            ))
          )}
        </div>

        {/* SubAgent Section */}
        <div className="subagent-section">
          <SubAgentFeed 
            messages={subAgentMessages}
            onClear={onClearSubAgentMessages}
            onFilesUpdate={onFilesUpdate}
          />
        </div>
      </div>
    </div>
  );
};