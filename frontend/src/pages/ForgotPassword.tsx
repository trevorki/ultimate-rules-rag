import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import Layout from '../components/Layout';

const ForgotPassword: React.FC = () => {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('submitting');
    setError('');

    try {
      await apiClient.forgotPassword(email);
      setStatus('success');
      // Keep success message visible for 3 seconds before redirecting
      setTimeout(() => navigate('/login'), 3000);
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
          <h1 className="text-2xl font-bold mb-6 text-center text-light-theme dark:text-dark-theme">
            Reset Password
          </h1>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-light-theme dark:text-dark-theme">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={status === 'submitting'}
                className="mt-1 block w-full rounded-md border-0 px-3 py-2 
                  chat-background-light dark:chat-background-dark 
                  text-light-theme dark:text-dark-theme
                  focus:ring-2 focus:ring-message-user-light dark:focus:ring-message-user-dark"
                required
              />
            </div>
            
            {status === 'error' && (
              <p className="text-red-500 text-sm">{error}</p>
            )}
            
            {status === 'success' && (
              <p className="text-green-500 text-sm">
                If an account exists with this email, you will receive password reset instructions.
              </p>
            )}
            
            <button
              type="submit"
              disabled={status === 'submitting'}
              className="button-action w-full py-2 px-4 rounded-md disabled:opacity-50"
            >
              {status === 'submitting' ? 'Sending...' : 'Reset Password'}
            </button>
            
            <div className="text-center mt-4">
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300"
              >
                Back to Login
              </button>
            </div>
          </form>
        </div>
      </div>
    </Layout>
  );
};

export default ForgotPassword; 
