import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listFiles } from '../services/api';
import './Dashboard.css';

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState({
    totalFiles: 0,
    webVitalsFiles: 0,
    jmeterFiles: 0,
    uiPerformanceFiles: 0
  });

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const result = await listFiles();
      const files = result.files || [];
      
      setStats({
        totalFiles: files.length,
        webVitalsFiles: files.filter(f => f.category === 'web_vitals').length,
        jmeterFiles: files.filter(f => f.category === 'jmeter').length,
        uiPerformanceFiles: files.filter(f => f.category === 'ui_performance').length
      });
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const statCards = [
    { title: 'Total Files', value: stats.totalFiles, icon: '📁', color: '#3498db', link: '/files' },
    { title: 'Web Vitals', value: stats.webVitalsFiles, icon: '⚡', color: '#2ecc71', link: '/files' },
    { title: 'JMeter Tests', value: stats.jmeterFiles, icon: '🧪', color: '#e74c3c', link: '/files' },
    { title: 'UI Performance', value: stats.uiPerformanceFiles, icon: '🎯', color: '#f39c12', link: '/files' },
  ];

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <p>Welcome to your Performance Analysis Dashboard</p>
      </div>

      <div className="stats-grid">
        {statCards.map((card, index) => (
          <Link to={card.link} key={index} className="stat-card" style={{ borderLeftColor: card.color }}>
            <div className="stat-icon" style={{ background: card.color }}>{card.icon}</div>
            <div className="stat-content">
              <h3>{card.value}</h3>
              <p>{card.title}</p>
            </div>
          </Link>
        ))}
      </div>

      <div className="recent-activity">
        <h2>Recent Activity</h2>
        <div className="activity-list">
          <div className="activity-item">
            <span className="activity-icon">✅</span>
            <div className="activity-content">
              <p className="activity-title">System initialized successfully</p>
              <p className="activity-time">Just now</p>
            </div>
          </div>
          <div className="activity-item">
            <span className="activity-icon">📊</span>
            <div className="activity-content">
              <p className="activity-title">Ready to analyze performance data</p>
              <p className="activity-time">Just now</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;












