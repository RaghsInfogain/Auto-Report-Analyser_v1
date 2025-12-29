import React, { createContext, useContext, useState, useEffect } from 'react';

interface User {
  username: string;
  email: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    // Check if user is stored in localStorage
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
  }, []);

  const login = async (username: string, password: string): Promise<boolean> => {
    // Predefined user account
    const predefinedUsers: Record<string, { password: string; email: string; role: string }> = {
      'raghskmr': {
        password: 'password',
        email: 'raghskmr@autoreportanalyzer.com',
        role: 'Performance Architect'
      }
    };

    // Check if it's a predefined user
    if (predefinedUsers[username]) {
      if (predefinedUsers[username].password === password) {
        const newUser: User = {
          username,
          email: predefinedUsers[username].email,
          role: predefinedUsers[username].role
        };
        setUser(newUser);
        localStorage.setItem('user', JSON.stringify(newUser));
        return true;
      }
      return false;
    }

    // For demo purposes, accepting any other username with password "password"
    if (password === 'password') {
      const newUser: User = {
        username,
        email: `${username}@example.com`,
        role: 'Performance Architect'
      };
      setUser(newUser);
      localStorage.setItem('user', JSON.stringify(newUser));
      return true;
    }
    return false;
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('user');
  };

  const value = {
    user,
    login,
    logout,
    isAuthenticated: !!user
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

