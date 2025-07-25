import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import LoginPage from './components/auth/LoginPage';
import AdminLayout from './components/layouts/AdminLayout';
import AgentLayout from './components/layouts/AgentLayout';
import LoadingSpinner from './components/ui/LoadingSpinner';
import './App.css';

// Protected Route Component
const ProtectedRoute = ({ children, allowedRoles = [] }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return children;
};

// Main App Router
const AppRouter = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <Routes>
      {/* Public Routes */}
      <Route 
        path="/login" 
        element={!user ? <LoginPage /> : <Navigate to="/" replace />} 
      />
      
      {/* Protected Routes */}
      <Route
        path="/admin/*"
        element={
          <ProtectedRoute allowedRoles={['admin', 'supervisor']}>
            <AdminLayout />
          </ProtectedRoute>
        }
      />
      
      <Route
        path="/agent/*"
        element={
          <ProtectedRoute allowedRoles={['agent']}>
            <AgentLayout />
          </ProtectedRoute>
        }
      />
      
      {/* Default Route - Redirect based on role */}
      <Route
        path="/"
        element={
          user ? (
            user.role === 'agent' ? (
              <Navigate to="/agent" replace />
            ) : (
              <Navigate to="/admin" replace />
            )
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      
      {/* Unauthorized Route */}
      <Route
        path="/unauthorized"
        element={
          <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full space-y-8">
              <div className="text-center">
                <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
                  Access Denied
                </h2>
                <p className="mt-2 text-sm text-gray-600">
                  You don't have permission to access this page.
                </p>
              </div>
            </div>
          </div>
        }
      />
      
      {/* 404 Route */}
      <Route
        path="*"
        element={
          <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full space-y-8">
              <div className="text-center">
                <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
                  Page Not Found
                </h2>
                <p className="mt-2 text-sm text-gray-600">
                  The page you're looking for doesn't exist.
                </p>
              </div>
            </div>
          </div>
        }
      />
    </Routes>
  );
};

function App() {
  return (
    <Router>
      <AuthProvider>
        <div className="App">
          <AppRouter />
        </div>
      </AuthProvider>
    </Router>
  );
}

export default App;

