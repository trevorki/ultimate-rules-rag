import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';

export const ChangePassword: React.FC = () => {
  const [email, setEmail] = useState('');
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient.changePassword(email, oldPassword, newPassword);
      setSuccess(true);
      setTimeout(() => navigate('/chat'), 2000);
    } catch (err) {
      setError('Failed to change password');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center chat-background-light dark:chat-background-dark">
      <div className="header-footer-light dark:header-footer-dark p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 className="text-2xl font-bold mb-6 text-center text-light-theme dark:text-dark-theme">Change Password</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-light-theme dark:text-dark-theme">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-md border-0 px-3 py-2 
                chat-background-light dark:chat-background-dark 
                text-light-theme dark:text-dark-theme
                focus:ring-2 focus:ring-message-user-light dark:focus:ring-message-user-dark"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-light-theme dark:text-dark-theme">Old Password</label>
            <input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border-0 px-3 py-2 
                chat-background-light dark:chat-background-dark 
                text-light-theme dark:text-dark-theme
                focus:ring-2 focus:ring-message-user-light dark:focus:ring-message-user-dark"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-light-theme dark:text-dark-theme">New Password</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border-0 px-3 py-2 
                chat-background-light dark:chat-background-dark 
                text-light-theme dark:text-dark-theme
                focus:ring-2 focus:ring-message-user-light dark:focus:ring-message-user-dark"
            />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          {success && <p className="text-green-500 text-sm">Password changed successfully!</p>}
          <button
            type="submit"
            className="button-action w-full py-2 px-4 rounded-md"
          >
            Change Password
          </button>
        </form>
      </div>
    </div>
  );
}; 