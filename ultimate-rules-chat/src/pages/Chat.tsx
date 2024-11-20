import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient, ChatMessage } from '../api/client';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';

type CodeProps = {
  inline?: boolean;
  className?: string;
  children?: React.ReactNode;
};

export function Chat() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string>('');
  const navigate = useNavigate();
  const messagesEndRef = useRef<null | HTMLDivElement>(null);
  const [isDarkMode, setIsDarkMode] = useState(true);

  const handleLogout = useCallback(() => {
    localStorage.removeItem('token');
    navigate('/login');
  }, [navigate]);

  const initializeConversation = useCallback(async () => {
    try {
      const { conversation_id } = await apiClient.createConversation();
      setConversationId(conversation_id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
      if (error instanceof Error && error.message.includes('401')) {
        handleLogout();
      }
    }
  }, [handleLogout]);

  useEffect(() => {
    initializeConversation();
  }, [initializeConversation]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDarkMode);
  }, [isDarkMode]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    const newMessage: ChatMessage = { role: 'user', content: message };
    setMessages(prev => [...prev, newMessage]);
    setMessage('');

    try {
      const response = await apiClient.sendMessage(message, conversationId);
      const aiMessage: ChatMessage = { role: 'assistant', content: response.message };
      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      if (error instanceof Error && error.message.includes('401')) {
        handleLogout();
      }
    }
  };

  const toggleTheme = () => {
    setIsDarkMode(prev => !prev);
  };

  const markdownComponents: Components = {
    p: ({ children }) => (
      <p className="mb-4 last:mb-0">{children}</p>
    ),
    code: ({ inline, className, children }: CodeProps) => {
      return inline ? (
        <code className={`bg-opacity-20 ${isDarkMode ? 'bg-dark-surface' : 'bg-light-surface'} px-1.5 py-0.5 rounded text-sm`}>
          {children}
        </code>
      ) : (
        <pre className={`${isDarkMode ? 'bg-dark-surface' : 'bg-light-surface'} rounded-md p-4 my-4 overflow-x-auto`}>
          <code className={className}>
            {children}
          </code>
        </pre>
      );
    },
    ul: ({ children }) => (
      <ul className="list-disc list-outside ml-4 mb-4 space-y-2">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal list-outside ml-4 mb-4 space-y-2">{children}</ol>
    ),
    li: ({ children }) => (
      <li className="ml-2">{children}</li>
    ),
    h1: ({ children }) => (
      <h1 className="text-2xl font-bold mb-4">{children}</h1>
    ),
    h2: ({ children }) => (
      <h2 className="text-xl font-bold mb-3">{children}</h2>
    ),
    h3: ({ children }) => (
      <h3 className="text-lg font-bold mb-2">{children}</h3>
    ),
    a: ({ href, children }) => (
      <a href={href} className="text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    ),
    blockquote: ({ children }) => (
      <blockquote className="border-l-4 border-gray-500 pl-4 my-4 italic">
        {children}
      </blockquote>
    ),
    strong: ({ children }) => (
      <strong className="font-bold">{children}</strong>
    ),
  };

  return (
    <div className={`h-screen flex flex-col ${isDarkMode ? 'chat-background-dark text-dark-theme' : 'chat-background-light text-light-theme'}`}>
      <header className={`h-14 ${
        isDarkMode ? 'header-footer-dark' : 'header-footer-light'
      } shadow-md fixed top-0 left-0 right-0 z-50 border-b`}>
        <div className="h-full px-4 flex justify-between items-center">
          <h1 className="text-xl font-semibold">
            Ultimate Rules Chat
          </h1>
          <div className="flex items-center gap-3">
            <button
              onClick={toggleTheme}
              className={`h-8 w-8 rounded-md shadow-md transition-all duration-200
                ${isDarkMode 
                  ? 'bg-[#f4ece2] text-[#2a332d]'
                  : 'bg-[#2a332d] text-[#f5f5f0]'
                } hover:bg-opacity-80 flex items-center justify-center`}
            >
              {isDarkMode ? '☀️' : '🌙'}
            </button>
            <button
              onClick={handleLogout}
              className="button-action px-4 py-1.5 rounded-md text-sm"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className={`flex-1 mt-14 mb-16 overflow-y-auto ${isDarkMode ? 'chat-background-dark' : 'chat-background-light'}`}>
        <div className="max-w-2xl mx-auto px-4 py-6">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} mb-4`}
            >
              <div
                className={`max-w-[80%] px-4 py-2 shadow-md ${
                  msg.role === 'user'
                    ? isDarkMode 
                      ? 'message-user-dark text-dark-theme'
                      : 'message-user-light text-light-theme'
                    : isDarkMode
                      ? 'message-ai-dark text-dark-theme'
                      : 'message-ai-light text-light-theme'
                } rounded-t-2xl ${
                  msg.role === 'user' ? 'rounded-l-2xl' : 'rounded-r-2xl'
                }`}
              >
                {msg.role === 'user' ? (
                  <p className="text-[15px] whitespace-pre-wrap">{msg.content}</p>
                ) : (
                  <div className="text-[15px] prose max-w-none dark:prose-invert">
                    <ReactMarkdown components={markdownComponents}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </main>

      <footer className={`fixed bottom-0 left-0 right-0 ${
        isDarkMode 
          ? 'header-footer-dark' 
          : 'header-footer-light'
      } border-t p-3`}>
        <div className="max-w-2xl mx-auto">
          <form onSubmit={handleSubmit} className="flex items-center gap-2">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className={`flex-1 rounded-full px-4 py-2 text-[15px] focus:outline-none focus:ring-2 focus:ring-light-accent ${
                isDarkMode 
                  ? 'chat-background-dark text-dark-theme placeholder-gray-400' 
                  : 'chat-background-light text-light-theme placeholder-gray-500'
              }`}
              placeholder="Message"
            />
            <button
              type="submit"
              className="button-action px-6 py-2 rounded-full text-sm font-medium"
            >
              Send
            </button>
          </form>
        </div>
      </footer>
    </div>
  );
} 