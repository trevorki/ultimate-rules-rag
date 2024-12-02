import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import Layout from '../components/Layout';

const SignUp: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    try {
      await apiClient.signup(email, password);
      navigate('/login');
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to create account');
      }
    }
  };

  return (
    <Layout>
      <div className="min-h-screen flex items-center justify-center chat-background-light dark:chat-background-dark">
        <div className="header-footer-light dark:header-footer-dark p-8 rounded-lg shadow-md w-full max-w-md">
          <h1 className="text-2xl font-bold mb-6 text-center text-black dark:text-dark-theme">Sign Up</h1>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-black dark:text-dark-theme">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full rounded-md border-0 px-3 py-2 
                  chat-background-light dark:chat-background-dark 
                  text-black dark:text-dark-theme
                  focus:ring-2 focus:ring-message-user-light dark:focus:ring-message-user-dark"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-black dark:text-dark-theme">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full rounded-md border-0 px-3 py-2 
                  chat-background-light dark:chat-background-dark 
                  text-black dark:text-dark-theme
                  focus:ring-2 focus:ring-message-user-light dark:focus:ring-message-user-dark"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-black dark:text-dark-theme">Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="mt-1 block w-full rounded-md border-0 px-3 py-2 
                  chat-background-light dark:chat-background-dark 
                  text-black dark:text-dark-theme
                  focus:ring-2 focus:ring-message-user-light dark:focus:ring-message-user-dark"
              />
            </div>
            {error && <p className="text-red-500 text-sm">{error}</p>}
            <button
              type="submit"
              className="button-action w-full py-2 px-4 rounded-md"
            >
              Sign Up
            </button>
            <div className="text-center mt-4">
              <Link 
                to="/login" 
                className="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 text-sm"
              >
                Already have an account? Login
              </Link>
            </div>
          </form>
        </div>
      </div>
    </Layout>
  );
};

export default SignUp; 
