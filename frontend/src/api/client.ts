import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests if it exists
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Add response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      throw new Error('401 Unauthorized - Token expired');
    }
    throw error;
  }
);

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface ChatMessage {
  role: string;
  content: string;
}

export interface ChatResponse {
  message: string;
  conversation_id: string;
}

export const apiClient = {
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await api.post<LoginResponse>('/token', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  },

  createConversation: async () => {
    const response = await api.post<{ conversation_id: string }>('/conversation');
    return response.data;
  },

  sendMessage: async (message: string, conversationId: string): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>('/chat', {
      message,
      conversation_id: conversationId,
    });
    return response.data;
  },

  getConversationHistory: async (conversationId: string): Promise<ChatMessage[]> => {
    const response = await api.get<{ messages: ChatMessage[] }>(`/conversation/${conversationId}`);
    return response.data.messages;
  },

  changePassword: async (email: string, oldPassword: string, newPassword: string) => {
    const response = await api.post('/change-password', {
      email,
      old_password: oldPassword,
      new_password: newPassword,
    });
    return response.data;
  },

  signup: async (email: string, password: string): Promise<void> => {
    await api.post('/signup', {
      email,
      password,
    });
  },

  forgotPassword: async (email: string): Promise<void> => {
    await api.post('/forgot-password', {
      email,
    });
  },

  verifyEmail: async (token: string): Promise<void> => {
    await api.get(`/verify?token=${token}`);
  },

  resetPassword: async (token: string, newPassword: string): Promise<void> => {
    await api.post('/reset-password', {
      token,
      new_password: newPassword,
    });
  },
}; 
