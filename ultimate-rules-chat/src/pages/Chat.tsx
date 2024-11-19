import React, { useState, useEffect, useRef } from 'react';
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

  useEffect(() => {
    initializeConversation();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const initializeConversation = async () => {
    try {
      const { conversation_id } = await apiClient.createConversation();
      setConversationId(conversation_id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
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
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const markdownComponents: Components = {
    p: ({ children }) => (
      <p className="mb-4 last:mb-0">{children}</p>
    ),
    code: ({ inline, className, children }: CodeProps) => {
      // const match = /language-(\w+)/.exec(className || '');
      return inline ? (
        <code className="bg-gray-800 px-1.5 py-0.5 rounded text-sm">
          {children}
        </code>
      ) : (
        <pre className="bg-gray-800 rounded-md p-4 my-4 overflow-x-auto">
          <code className={className}>
            {children}
          </code>
        </pre>
      );
    },
    ul: ({ children }) => (
      // <ul className="list-disc list-inside mb-4 space-y-2">{children}</ul>
      <ul className="list-disc list-outside ml-0 mb-4 space-y-2">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal list-inside mb-4 space-y-2">{children}</ol>
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
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Fixed Header */}
      <header className="h-14 bg-gray-800 shadow-md fixed top-0 left-0 right-0 z-50">
        <div className="h-full px-4 flex justify-between items-center">
          <h1 className="text-xl font-semibold text-gray-50">Ultimate Rules Chat</h1>
          <button
            onClick={handleLogout}
            className="bg-red-700 text-white px-4 py-1.5 rounded-md hover:bg-red-800 transition-all duration-200 text-sm"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Chat Container */}
      <main className="flex-1 mt-14 mb-16 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-4 py-6">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} mb-4`}
            >
              <div
                className={`max-w-[80%] px-4 py-2 shadow-md ${
                  msg.role === 'user'
                    ? 'bg-blue-700 rounded-t-2xl rounded-l-2xl'
                    : 'bg-gray-700 rounded-t-2xl rounded-r-2xl'
                }`}
              >
                {msg.role === 'user' ? (
                  <p className="text-white text-[15px] whitespace-pre-wrap">{msg.content}</p>
                ) : (
                  <div className="text-white text-[15px] prose prose-invert max-w-none">
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

      {/* Fixed Input Area */}
      <footer className="fixed bottom-0 left-0 right-0 bg-gray-800 border-t border-gray-700 p-3">
        <div className="max-w-2xl mx-auto">
          <form onSubmit={handleSubmit} className="flex items-center gap-2">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="flex-1 bg-gray-700 text-white rounded-full px-4 py-2 text-[15px] focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Message"
            />
            <button
              type="submit"
              className="bg-blue-600 text-white px-6 py-2 rounded-full hover:bg-blue-700 transition-all duration-200 font-medium"
            >
              Send
            </button>
          </form>
        </div>
      </footer>
    </div>
  );
} 