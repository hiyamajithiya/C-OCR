/**
 * Main App component with routing and layout.
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline, Box, CircularProgress } from '@mui/material';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import theme from '@/theme/theme';

// Pages
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import DocumentsPage from '@/pages/DocumentsPage';
import TemplatesPage from '@/pages/TemplatesPage';
import TemplateBuilderPage from '@/pages/TemplateBuilderPage';
import ExtractionResultsPage from '@/pages/ExtractionResultsPage';
import APIKeysPage from '@/pages/APIKeysPage';
import UsersPage from '@/pages/UsersPage';
import AuditLogsPage from '@/pages/AuditLogsPage';
import EntitiesPage from '@/pages/EntitiesPage';
import AnalyticsPage from '@/pages/AnalyticsPage';
import SettingsPage from '@/pages/SettingsPage';
import PortalLoginPage from '@/pages/PortalLoginPage';
import PortalDashboardPage from '@/pages/PortalDashboardPage';
import Layout from '@/components/Layout';
import PortalLayout from '@/components/PortalLayout';
import { PortalAuthProvider, usePortalAuth } from '@/contexts/PortalAuthContext';

// Loading screen component
const LoadingScreen: React.FC = () => (
  <Box
    sx={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      bgcolor: 'background.default',
      gap: 2,
    }}
  >
    <CircularProgress size={48} thickness={4} />
  </Box>
);

// Protected Route Component
const ProtectedRoute: React.FC<{ children: React.ReactNode; roles?: string[] }> = ({
  children,
  roles,
}) => {
  const { isAuthenticated, isLoading, hasRole } = useAuth();

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (roles && !hasRole(roles)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

// Portal Protected Route
const PortalProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = usePortalAuth();

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/portal/login" replace />;
  }

  return <>{children}</>;
};

function AppRoutes() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      {/* Public Routes */}
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />}
      />

      {/* Protected Routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="documents/:documentId/extractions" element={<ExtractionResultsPage />} />
        <Route path="templates" element={<TemplatesPage />} />
        <Route path="templates/:templateId/builder" element={<TemplateBuilderPage />} />
        <Route
          path="api-keys"
          element={
            <ProtectedRoute roles={['admin']}>
              <APIKeysPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="users"
          element={
            <ProtectedRoute roles={['admin']}>
              <UsersPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="audit-logs"
          element={
            <ProtectedRoute roles={['admin']}>
              <AuditLogsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="entities"
          element={
            <ProtectedRoute roles={['admin']}>
              <EntitiesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="analytics"
          element={
            <ProtectedRoute roles={['admin']}>
              <AnalyticsPage />
            </ProtectedRoute>
          }
        />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      {/* Portal Routes */}
      <Route
        path="/portal/login"
        element={<PortalLoginPage />}
      />
      <Route
        path="/portal"
        element={
          <PortalProtectedRoute>
            <PortalLayout />
          </PortalProtectedRoute>
        }
      >
        <Route path="dashboard" element={<PortalDashboardPage />} />
      </Route>

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <PortalAuthProvider>
          <Router>
            <AppRoutes />
          </Router>
        </PortalAuthProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
