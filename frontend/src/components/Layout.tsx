import React, { useState, useEffect } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ChatBot from './ChatBot';
import './Layout.css';

const Layout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [analyzedFiles, setAnalyzedFiles] = useState<Record<string, any>>({});

  // Load analyzed files for chatbot context
  useEffect(() => {
    const storedResults = localStorage.getItem('analysisResults');
    if (storedResults) {
      try {
        const parsed = JSON.parse(storedResults);
        setAnalyzedFiles(parsed);
      } catch (error) {
        console.error('Error loading analysis results:', error);
      }
    }
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="layout">
      {/* Sidebar */}
      <aside className={`sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <h2>Auto Report Analyzer</h2>
          <button 
            className="toggle-btn"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          >
            {isSidebarOpen ? '◀' : '▶'}
          </button>
        </div>

        <nav className="sidebar-nav">
          <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            <span className="nav-icon">📊</span>
            {isSidebarOpen && <span className="nav-text">Dashboard</span>}
          </NavLink>

          <NavLink to="/files" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            <span className="nav-icon">📁</span>
            {isSidebarOpen && <span className="nav-text">My Files</span>}
          </NavLink>

          <NavLink to="/ai-chat" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            <span className="nav-icon">🤖</span>
            {isSidebarOpen && <span className="nav-text">AI Assistant</span>}
          </NavLink>
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar">{user?.username?.charAt(0).toUpperCase()}</div>
            {isSidebarOpen && (
              <div className="user-details">
                <div className="user-name">{user?.username}</div>
                <div className="user-role">{user?.role}</div>
              </div>
            )}
          </div>
          <button onClick={handleLogout} className="logout-btn">
            <span className="nav-icon">🚪</span>
            {isSidebarOpen && <span>Logout</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="top-bar">
          <h1>Performance Analysis Platform</h1>
          <div className="header-actions">
            <span className="user-greeting">Welcome, {user?.username}!</span>
          </div>
        </header>

        <div className="content-area">
          <Outlet />
        </div>
      </main>
      <ChatBot analyzedFiles={analyzedFiles} />
    </div>
  );
};

export default Layout;

