import { ThreadInfo, ChatMessage } from './types';

const API_BASE = '/api';

export class ApiClient {
  static async getThreads(): Promise<ThreadInfo[]> {
    const response = await fetch(`${API_BASE}/threads`);
    if (!response.ok) {
      throw new Error('Failed to fetch threads');
    }
    return response.json();
  }

  static async createThread(title?: string): Promise<ThreadInfo> {
    const response = await fetch(`${API_BASE}/threads`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title }),
    });
    if (!response.ok) {
      throw new Error('Failed to create thread');
    }
    return response.json();
  }

  static async deleteThread(threadId: string): Promise<void> {
    const response = await fetch(`${API_BASE}/threads/${threadId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to delete thread');
    }
  }

  static async getThreadMessages(threadId: string): Promise<{
    messages: ChatMessage[];
    files: Record<string, string[]>;
    thread_id: string;
  }> {
    const response = await fetch(`${API_BASE}/threads/${threadId}/messages`);
    if (!response.ok) {
      throw new Error('Failed to fetch messages');
    }
    return response.json();
  }

  static async stopChat(threadId: string): Promise<void> {
    const response = await fetch(`${API_BASE}/chat/stop`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ thread_id: threadId }),
    });
    if (!response.ok) {
      throw new Error('Failed to stop chat');
    }
  }

  static async streamChat(
    threadId: string, 
    message: string,
    onEvent: (data: any) => void,
    onError: (error: any) => void,
    onComplete: () => void
  ): Promise<() => void> {
    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          thread_id: threadId,
          message: message,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body reader available');
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let isReading = true;

      const readLoop = async () => {
        while (isReading) {
          try {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            
            // Process complete SSE events
            let eventEnd;
            while ((eventEnd = buffer.indexOf('\n\n')) !== -1) {
              const eventData = buffer.slice(0, eventEnd);
              buffer = buffer.slice(eventEnd + 2);
              
              if (eventData.trim()) {
                try {
                  // Parse SSE format
                  const lines = eventData.split('\n');
                  let data = '';
                  
                  for (const line of lines) {
                    if (line.startsWith('data:')) {
                      data += line.slice(5).trim();
                    }
                  }
                  
                  if (data) {
                    const parsedData = JSON.parse(data);
                    onEvent(parsedData);
                  }
                } catch (parseError) {
                  console.error('Failed to parse SSE event:', parseError);
                }
              }
            }
          } catch (readError) {
            if (isReading) {
              onError(readError);
            }
            break;
          }
        }
        
        onComplete();
      };

      readLoop();

      // Return stop function
      return () => {
        isReading = false;
        reader.cancel();
      };

    } catch (error) {
      onError(error);
      return () => {}; // No-op stop function
    }
  }
}