import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import DocumentEditor from './pages/DocumentEditor';
import ReviewQueue from './pages/ReviewQueue';
import ReviewTemplateManager from './pages/ReviewTemplateManager';
import ReviewStatsDashboard from './pages/ReviewStatsDashboard';
import { CircularProgress, Box } from '@mui/material';

const PrivateRoute = ({ children, roles }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }
  
  if (!user) return <Navigate to="/login" />;
  
  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/" />;
  }
  
  return children;
};

const App = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <div>
      {user && <Navbar />}
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route 
          path="/" 
          element={
            <PrivateRoute>
              <Dashboard />
            </PrivateRoute>
          } 
        />
        <Route 
          path="/document/:docId" 
          element={
            <PrivateRoute>
              <DocumentEditor />
            </PrivateRoute>
          } 
        />
        <Route 
          path="/reviews" 
          element={
            <PrivateRoute>
              <ReviewQueue />
            </PrivateRoute>
          } 
        />
        <Route 
          path="/templates" 
          element={
            <PrivateRoute>
              <ReviewTemplateManager />
            </PrivateRoute>
          } 
        />
        <Route 
          path="/stats" 
          element={
            <PrivateRoute roles={['reviewer', 'admin']}>
              <ReviewStatsDashboard />
            </PrivateRoute>
          } 
        />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </div>
  );
};

export default App;
