import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listFiles } from '../services/api';
import PageShell from '../components/PageShell';
import './Dashboard.css';

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState({
    totalFiles: 0,
    webVitalsFiles: 0,
    jmeterFiles: 0,
    uiPerformanceFiles: 0,
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
        webVitalsFiles: files.filter((f) => f.category === 'web_vitals').length,
        jmeterFiles: files.filter((f) => f.category === 'jmeter').length,
        uiPerformanceFiles: files.filter((f) => f.category === 'ui_performance').length,
      });
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const kpiCards = [
    { title: 'Total Files', value: stats.totalFiles, tone: 'bl' as const, link: '/files', icon: 'ti ti-folder' },
    { title: 'Web Vitals', value: stats.webVitalsFiles, tone: 'gn' as const, link: '/web-vitals', icon: 'ti ti-bolt' },
    { title: 'JMeter Tests', value: stats.jmeterFiles, tone: 'am' as const, link: '/jmeter', icon: 'ti ti-flask' },
    { title: 'UI Performance', value: stats.uiPerformanceFiles, tone: 'pu' as const, link: '/files', icon: 'ti ti-device-desktop-analytics' },
  ];

  return (
    <PageShell
      iconClass="ti ti-layout-dashboard"
      iconTone="bl"
      title="Performance Overview"
      subtitle="Upload, analyze, and compare load tests, Web Vitals, and release intelligence in one workspace."
      actions={
        <button type="button" className="ent-btn ent-btn-ghost" onClick={loadStats}>
          <i className="ti ti-refresh" /> Refresh
        </button>
      }
    >
      <div className="ent-slb">Key metrics</div>
      <div className="ent-kstr dashboard-kpi" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        {kpiCards.map((card) => (
          <Link key={card.title} to={card.link} className="ent-kpi">
            <div className="ent-klb">
              <i className={card.icon} style={{ fontSize: 11, marginRight: 3 }} />
              {card.title}
            </div>
            <div className={`ent-kval ${card.tone}`}>{card.value}</div>
          </Link>
        ))}
      </div>

      <div className="ent-g2">
        <div className="ent-card">
          <div className="ent-card-hd">
            <h2>
              <i className="ti ti-upload" style={{ marginRight: 5, color: 'var(--ink4)' }} />
              Quick actions
            </h2>
          </div>
          <div className="ent-card-bd" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Link to="/jmeter" className="ent-btn ent-btn-primary" style={{ justifyContent: 'center' }}>
              <i className="ti ti-flask" /> JMeter test results
            </Link>
            <Link to="/web-vitals" className="ent-btn ent-btn-ghost" style={{ justifyContent: 'center' }}>
              <i className="ti ti-bolt" /> Web Vitals reports
            </Link>
            <Link to="/performance-test-compare" className="ent-btn ent-btn-ghost" style={{ justifyContent: 'center' }}>
              <i className="ti ti-scale" /> Baseline vs candidate
            </Link>
            <Link to="/compare" className="ent-btn ent-btn-ghost" style={{ justifyContent: 'center' }}>
              <i className="ti ti-arrows-left-right" /> Compare runs
            </Link>
          </div>
        </div>

        <div className="ent-card">
          <div className="ent-card-hd">
            <h2>
              <i className="ti ti-activity" style={{ marginRight: 5, color: 'var(--ink4)' }} />
              Recent activity
            </h2>
          </div>
          <div className="ent-card-bd">
            <div className="ent-alrt ent-alrt-gn" style={{ marginBottom: 8 }}>
              <i className="ti ti-check" style={{ color: 'var(--gn)', marginTop: 2 }} />
              <div>
                <strong style={{ fontSize: 11.5 }}>System ready</strong>
                <p style={{ fontSize: 11, marginTop: 2, color: 'var(--ink3)' }}>
                  Platform initialized — upload JTL/CSV or Lighthouse JSON to generate enterprise reports.
                </p>
              </div>
            </div>
            <div className="ent-alrt ent-alrt-bl">
              <i className="ti ti-chart-bar" style={{ color: 'var(--bl)', marginTop: 2 }} />
              <div>
                <strong style={{ fontSize: 11.5 }}>Reports use PerfSuite styling</strong>
                <p style={{ fontSize: 11, marginTop: 2, color: 'var(--ink3)' }}>
                  HTML reports for JMeter, Web Vitals, and comparisons follow the enterprise wireframe v4 design.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </PageShell>
  );
};

export default Dashboard;
