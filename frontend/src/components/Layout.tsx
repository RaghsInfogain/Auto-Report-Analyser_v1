import React, { useState, useEffect } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ChatBot from './ChatBot';
import './Layout.css';

const Layout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [analyzedFiles, setAnalyzedFiles] = useState<Record<string, unknown>>({});

  useEffect(() => {
    const storedResults = localStorage.getItem('analysisResults');
    if (storedResults) {
      try {
        setAnalyzedFiles(JSON.parse(storedResults));
      } catch (error) {
        console.error('Error loading analysis results:', error);
      }
    }
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const initial = user?.username?.charAt(0).toUpperCase() ?? '?';
  const layoutClass = `layout ${sidebarOpen ? 'sidebar-open' : 'sidebar-collapsed'}`;

  const navLink = (to: string, icon: string, label: string, useTabler = true) => (
    <NavLink
      to={to}
      className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}
      title={label}
    >
      <span className="nav-icon">
        {useTabler ? <i className={icon} /> : <span className="emoji">{icon}</span>}
      </span>
      <span className="nav-text">{label}</span>
    </NavLink>
  );

  return (
    <div className={layoutClass}>
      <header className="app-topbar">
        <button
          type="button"
          className="sidebar-toggle-top"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          <i className={sidebarOpen ? 'ti ti-layout-sidebar' : 'ti ti-layout-sidebar-right'} />
        </button>
        <div className="app-brand">
          <div className="app-brand-ic">
            <i className="ti ti-chart-infographic" />
          </div>
          <span>PerfSuite</span>
        </div>
        <span className="app-topbar-title">Performance Analysis Platform</span>
        <div className="app-topbar-right">
          <span className="app-topbar-greeting">Welcome, {user?.username}</span>
          <div className="app-avatar" title={user?.role}>{initial}</div>
        </div>
      </header>

      <aside className="sidebar">
        <nav className="sidebar-nav">
          <div className="sbs">
            <div className="sbl">Overview</div>
            {navLink('/dashboard', 'ti ti-layout-dashboard', 'Dashboard')}
            {navLink('/jmeter', 'ti ti-flask', 'JMeter Tests')}
            {navLink('/performance-test-compare', 'ti ti-scale', 'Perf test compare')}
            {navLink('/web-vitals', 'ti ti-bolt', 'Web Vitals')}
            {navLink('/files', 'ti ti-folder', 'All Files')}
          </div>

          <div className="sdiv" />

          <div className="sbs">
            <div className="sbl">Release Intelligence</div>
            {navLink('/baselines', 'ti ti-map-pin', 'Baselines')}
            {navLink('/compare', 'ti ti-arrows-left-right', 'Compare Runs')}
            {navLink('/release-decision', 'ti ti-target', 'Release Decision')}
          </div>

          <div className="sdiv" />

          <div className="sbs">
            <div className="sbl">Tools</div>
            {navLink('/ai-chat', 'ti ti-robot', 'AI Assistant')}
          </div>
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar">{initial}</div>
            <div className="user-details">
              <div className="user-name">{user?.username}</div>
              <div className="user-role">{user?.role}</div>
            </div>
          </div>
          <button type="button" onClick={handleLogout} className="logout-btn">
            <i className="ti ti-logout" />
            <span className="logout-label">Logout</span>
          </button>
        </div>
      </aside>

      <main className="main-content">
        <div className="content-area">
          <Outlet />
        </div>
      </main>

      <ChatBot analyzedFiles={analyzedFiles} />
    </div>
  );
};

export default Layout;
