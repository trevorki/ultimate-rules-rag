import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import Layout from '../components/Layout';

const Verify: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
  const [error, setError] = useState('');

  useEffect(() => {
    const verifyEmail = async () => {
      const token = searchParams.get('token');
      console.log('Verifying token:', token); // Debug log
      
      if (!token) {
        setStatus('error');
        setError('No verification token found');
        return;
      }

      try {
        await apiClient.verifyEmail(token);
        setStatus('success');
        // Store token in localStorage since this is a valid user now
        localStorage.setItem('token', token);
        // Redirect to chat page after 2 seconds
        setTimeout(() => {
          console.log('Redirecting to chat...'); // Debug log
          navigate('/chat');
        }, 2000);
      } catch (err) {
        console.error('Verification error:', err); // Debug log
        setStatus('error');
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('An unexpected error occurred during verification');
        }
      }
    };

    verifyEmail();
  }, [searchParams, navigate]);

  if (status === 'verifying') {
    return (
      <Layout>
        <div className="min-h-screen flex items-center justify-center">
          <div className="header-footer-light dark:header-footer-dark p-8 rounded-lg shadow-md w-full max-w-md">
            <h1 className="text-2xl font-bold mb-6 text-center text-light-theme dark:text-dark-theme">
              Email Verification
            </h1>
            <div className="text-center text-light-theme dark:text-dark-theme">
              <p>Verifying your email...</p>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (status === 'success') {
    return (
      <Layout>
        <div className="min-h-screen flex items-center justify-center">
          <div className="header-footer-light dark:header-footer-dark p-8 rounded-lg shadow-md w-full max-w-md">
            <h1 className="text-2xl font-bold mb-6 text-center text-light-theme dark:text-dark-theme">
              Email Verification
            </h1>
            <div className="text-center">
              <p className="text-green-600 dark:text-green-400 mb-4">
                Your email has been verified successfully!
              </p>
              <p className="text-light-theme dark:text-dark-theme">
                Redirecting to chat page...
              </p>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="min-h-screen flex items-center justify-center">
        <div className="header-footer-light dark:header-footer-dark p-8 rounded-lg shadow-md w-full max-w-md">
          <h1 className="text-2xl font-bold mb-6 text-center text-light-theme dark:text-dark-theme">
            Email Verification
          </h1>
          <div className="text-center">
            <p className="text-red-600 dark:text-red-400 mb-4">
              {error}
            </p>
            <button
              onClick={() => navigate('/login')}
              className="button-action px-4 py-2 rounded-md"
            >
              Go to Login
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Verify;