import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await apiClient.login(email, password);
      localStorage.setItem('token', response.access_token);
      navigate('/chat');
    } catch (err) {
      setError('Invalid email or password');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center chat-background-light dark:chat-background-dark">
      <div className="header-footer-light dark:header-footer-dark p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 className="text-2xl font-bold mb-6 text-center text-light-theme dark:text-dark-theme">Ultimate Rules Chat</h1>
        <h3 className="text-xl font-bold mb-6 text-center text-light-theme dark:text-dark-theme">Login</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-light-theme dark:text-dark-theme">Username</label>
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-md border-0 px-3 py-2 
                chat-background-light dark:chat-background-dark 
                text-light-theme dark:text-dark-theme
                focus:ring-2 focus:ring-message-user-light dark:focus:ring-message-user-dark"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-light-theme dark:text-dark-theme">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border-0 px-3 py-2 
                chat-background-light dark:chat-background-dark 
                text-light-theme dark:text-dark-theme
                focus:ring-2 focus:ring-message-user-light dark:focus:ring-message-user-dark"
            />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            className="button-action w-full py-2 px-4 rounded-md"
          >
            Login
          </button>
        </form>
      </div>
    </div>
  );
}; 