import React from 'react';
import { Plus, MessageSquare, Clock } from 'lucide-react';
import { ThreadInfo } from '../types';

interface HistoryPanelProps {
  threads: ThreadInfo[];
  activeThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onCreateThread: () => void;
  isLoading?: boolean;
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({
  threads,
  activeThreadId,
  onSelectThread,
  onCreateThread,
  isLoading = false,
}) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
      return date.toLocaleTimeString('zh-CN', { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } else if (diffDays === 1) {
      return '昨天';
    } else if (diffDays < 7) {
      return `${diffDays}天前`;
    } else {
      return date.toLocaleDateString('zh-CN', { 
        month: 'short', 
        day: 'numeric' 
      });
    }
  };

  return (
    <div className="history-panel">
      <div className="history-header">
        <h2>对话历史</h2>
        <button 
          className="new-chat-btn" 
          onClick={onCreateThread}
          disabled={isLoading}
        >
          <Plus size={16} />
          新对话
        </button>
      </div>
      
      <div className="history-list">
        {isLoading ? (
          <div className="loading-placeholder">
            <div className="loading">加载中...</div>
          </div>
        ) : threads.length === 0 ? (
          <div className="empty-state">
            <MessageSquare size={48} style={{ color: 'var(--text-muted)' }} />
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '1rem' }}>
              还没有对话记录
            </p>
          </div>
        ) : (
          threads.map((thread) => (
            <div
              key={thread.thread_id}
              className={`thread-item ${
                activeThreadId === thread.thread_id ? 'active' : ''
              }`}
              onClick={() => onSelectThread(thread.thread_id)}
            >
              <div className="thread-title">{thread.title}</div>
              <div className="thread-meta">
                <span>
                  <Clock size={12} style={{ marginRight: '0.25rem' }} />
                  {formatDate(thread.last_message_at || thread.created_at)}
                </span>
                <span>{thread.message_count} 条消息</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};