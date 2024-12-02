import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Chat from './pages/Chat';
import ChangePassword from './pages/ChangePassword';
import SignUp from './pages/SignUp';
import ForgotPassword from './pages/ForgotPassword';
import Verify from './pages/Verify';
import ResetPassword from './pages/ResetPassword';
import { ThemeProvider } from './contexts/ThemeContext';

function App() {
  return (
    <Router>
      <ThemeProvider>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/verify" element={<Verify />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
        </Routes>
      </ThemeProvider>
    </Router>
  );
}

export default App; 