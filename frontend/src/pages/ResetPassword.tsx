import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import Layout from '../components/Layout';

const ResetPassword: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    const token = searchParams.get('token');
    if (!token) {
      setError('Invalid reset link');
      return;
    }

    setStatus('submitting');

    try {
      await apiClient.resetPassword(token, newPassword);
      setStatus('success');
      
      // Store the token and redirect to chat
      localStorage.setItem('token', token);
      setTimeout(() => navigate('/chat'), 2000);
    } catch (err) {
      setStatus('error');
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred');
      }
    }
  };

  return (
    <Layout>
      <div className="min-h-screen flex items-center justify-center chat-background-light dark:chat-background-dark">
        <div className="header-footer-light dark:header-footer-dark p-8 rounded-lg shadow-md w-full max-w-md">
          <h1 className="text-2xl font-bold mb-6 text-center text-black dark:text-dark-theme">
            Reset Password
          </h1>
          
          {status === 'success' ? (
            <div className="text-center">
              <p className="text-green-500 mb-4">
                Password has been reset successfully!
              </p>
              <p className="text-black dark:text-dark-theme">
                Redirecting to chat...
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-black dark:text-dark-theme">
                  New Password
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="mt-1 block w-full rounded-md border-0 px-3 py-2 
                    chat-background-light dark:chat-background-dark 
                    text-black dark:text-dark-theme
                    focus:ring-2 focus:ring-message-user-light dark:focus:ring-message-user-dark"
                  required
                  minLength={8}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-black dark:text-dark-theme">
                  Confirm Password
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="mt-1 block w-full rounded-md border-0 px-3 py-2 
                    chat-background-light dark:chat-background-dark 
                    text-black dark:text-dark-theme
                    focus:ring-2 focus:ring-message-user-light dark:focus:ring-message-user-dark"
                  required
                  minLength={8}
                />
              </div>

              {error && (
                <p className="text-red-500 text-sm">{error}</p>
              )}

              <button
                type="submit"
                disabled={status === 'submitting'}
                className="button-action w-full py-2 px-4 rounded-md disabled:opacity-50"
              >
                {status === 'submitting' ? 'Resetting...' : 'Reset Password'}
              </button>
            </form>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default ResetPassword; 