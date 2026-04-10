/**
 * Authentication context for entity portal users.
 * Separate from admin AuthContext — uses portal-specific localStorage keys and API endpoints.
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiService } from '@/services/api';

interface PortalUser {
  id: number;
  name: string;
  email: string;
  entity_name: string;
}

interface PortalAuthContextType {
  portalUser: PortalUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const PortalAuthContext = createContext<PortalAuthContextType | undefined>(undefined);

export const usePortalAuth = () => {
  const context = useContext(PortalAuthContext);
  if (!context) {
    throw new Error('usePortalAuth must be used within PortalAuthProvider');
  }
  return context;
};

interface PortalAuthProviderProps {
  children: ReactNode;
}

export const PortalAuthProvider: React.FC<PortalAuthProviderProps> = ({ children }) => {
  const [portalUser, setPortalUser] = useState<PortalUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadUser = async () => {
      const token = localStorage.getItem('portal_access_token');
      const storedUser = localStorage.getItem('portal_user');

      if (token && storedUser) {
        try {
          const parsedUser = JSON.parse(storedUser) as PortalUser;
          setPortalUser(parsedUser);
        } catch (error) {
          console.error('Failed to parse stored portal user:', error);
          localStorage.removeItem('portal_access_token');
          localStorage.removeItem('portal_user');
          setPortalUser(null);
        }
      }

      setIsLoading(false);
    };

    loadUser();
  }, []);

  // Listen for 401 responses and redirect to portal login
  useEffect(() => {
    const handleUnauthorized = () => {
      // Only act if we thought we were authenticated
      if (portalUser) {
        localStorage.removeItem('portal_access_token');
        localStorage.removeItem('portal_user');
        setPortalUser(null);
        window.location.href = '/portal/login';
      }
    };

    window.addEventListener('portal-unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('portal-unauthorized', handleUnauthorized);
    };
  }, [portalUser]);

  const login = async (email: string, password: string) => {
    try {
      const response = await apiService.portalLogin(email, password);
      const { access_token, user: userData } = response;

      localStorage.setItem('portal_access_token', access_token);
      localStorage.setItem('portal_user', JSON.stringify(userData));
      setPortalUser(userData);
    } catch (error) {
      console.error('Portal login failed:', error);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('portal_access_token');
    localStorage.removeItem('portal_user');
    setPortalUser(null);
  };

  const value: PortalAuthContextType = {
    portalUser,
    isAuthenticated: !!portalUser,
    isLoading,
    login,
    logout,
  };

  return (
    <PortalAuthContext.Provider value={value}>{children}</PortalAuthContext.Provider>
  );
};
