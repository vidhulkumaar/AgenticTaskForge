import axios from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 600000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Citation {
  document_id: string;
  chunk_id: string;
  episode_title?: string;
  source_url?: string;
  content: string;
  timestamp_start?: number;
  speaker?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  citations?: Citation[];
  provider?: string;
  model?: string;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
}

export interface Artifact {
  id: string;
  type: string;
  content: string;
}

export interface ChatResponse {
  session_id: string;
  message_id: string;
  provider: string;
  model: string;
  content: string;
  created_at: string;
  citations: Citation[];
  artifact?: Artifact;
}

export const API = {
  createSession: async (title: string = "New Chat"): Promise<Session> => {
    const res = await apiClient.post<Session>('/sessions', { title });
    return res.data;
  },
  
  getSessions: async (): Promise<Session[]> => {
    const res = await apiClient.get<{items: Session[], total: number}>('/sessions');
    return res.data.items;
  },

  getMessages: async (sessionId: string): Promise<Message[]> => {
    const res = await apiClient.get<{items: Message[], total: number}>(`/sessions/${sessionId}/messages`);
    return res.data.items;
  },

  chat: async (
    sessionId: string,
    content: string,
    provider: string = "ollama"
  ): Promise<ChatResponse> => {
    const res = await apiClient.post<ChatResponse>(`/sessions/${sessionId}/chat`, {
      content,
      provider
    });
    return res.data;
  },
  
  generateEssay: async (
    sessionId: string,
    topic: string,
    provider: string = "claude"
  ): Promise<ChatResponse> => {
    // Re-use ChatResponse as it aligns with EssayResponse signature
    const res = await apiClient.post<ChatResponse>(`/sessions/${sessionId}/essay`, {
      topic,
      target_audience: "General founders and product managers",
      central_argument: "Growth requires a systematic approach.",
      provider
    });
    return res.data;
  }
};
