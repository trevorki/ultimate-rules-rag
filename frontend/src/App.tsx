import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Login } from './pages/Login';
import { Chat } from './pages/Chat';
import { ChangePassword } from './pages/ChangePassword';
import { useDarkMode } from './hooks/useDarkMode'

const PrivateRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

function App() {
  const { isDarkMode, setIsDarkMode } = useDarkMode()

  return (
    <div>
      <button
        onClick={() => setIsDarkMode(!isDarkMode)}
        className="rounded-lg p-2 hover:bg-gray-100 dark:hover:bg-gray-800"
      >
        {isDarkMode ? '🌞' : '🌙'}
      </button>
      
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/chat"
            element={
              <PrivateRoute>
                <Chat />
              </PrivateRoute>
            }
          />
          <Route
            path="/change-password"
            element={
              <PrivateRoute>
                <ChangePassword />
              </PrivateRoute>
            }
          />
          <Route path="/" element={<Navigate to="/chat" replace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App; 