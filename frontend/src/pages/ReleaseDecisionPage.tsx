import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import './ReleaseDecisionPage.css';

interface ComparisonDetails {
  comparison_id: string;
  baseline_id: string;
  current_run_id: string;
  overall_score: number;
  backend_score: number;
  frontend_score: number;
  reliability_score: number;
  verdict: string;
  regression_count: number;
  improvement_count: number;
  stable_count: number;
  summary_text: string;
  comparison_data: any;
}

interface Regression {
  metric_name: string;
  transaction_name?: string;
  category: string;
  baseline_value: number;
  current_value: number;
  change_percent: number;
  severity: string;
  change_type: string;
}

const ReleaseDecisionPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [comparisonId, setComparisonId] = useState('');
  const [comparison, setComparison] = useState<ComparisonDetails | null>(null);
  const [regressions, setRegressions] = useState<Regression[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedSeverity, setSelectedSeverity] = useState('all');

  useEffect(() => {
    const compParam = searchParams.get('comparison');
    if (compParam) {
      setComparisonId(compParam);
      fetchComparisonDetails(compParam);
      fetchRegressions(compParam);
    }
  }, [searchParams]);

  const fetchComparisonDetails = async (id: string) => {
    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/api/comparison/compare/result/${id}`);
      const data = await response.json();

      if (data.success) {
        setComparison(data.comparison);
      } else {
        setError('Failed to fetch comparison details');
      }
    } catch (err) {
      setError('Error connecting to server');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchRegressions = async (id: string, category?: string, severity?: string) => {
    try {
      let url = `http://localhost:8000/api/comparison/release/regressions/${id}`;
      const params = new URLSearchParams();
      if (category && category !== 'all') params.append('category', category);
      if (severity && severity !== 'all') params.append('severity', severity);
      if (params.toString()) url += '?' + params.toString();

      const response = await fetch(url);
      const data = await response.json();

      if (data.success) {
        setRegressions(data.regressions || []);
      }
    } catch (err) {
      console.error('Error fetching regressions:', err);
    }
  };

  useEffect(() => {
    if (comparisonId) {
      fetchRegressions(
        comparisonId,
        selectedCategory !== 'all' ? selectedCategory : undefined,
        selectedSeverity !== 'all' ? selectedSeverity : undefined
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCategory, selectedSeverity, comparisonId]);

  const getVerdictColor = (verdict: string) => {
    switch (verdict) {
      case 'approved': return '#10b981';
      case 'monitor': return '#f59e0b';
      case 'approval_needed': return '#ef4444';
      case 'blocked': return '#dc2626';
      default: return '#6b7280';
    }
  };

  const getVerdictText = (verdict: string) => {
    switch (verdict) {
      case 'approved': return '✅ Release Approved';
      case 'monitor': return '⚠️ Release Acceptable (Monitor)';
      case 'approval_needed': return '⚠️ Release Risky (Approval Required)';
      case 'blocked': return '❌ Release Blocked';
      default: return verdict;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return '#10b981';
    if (score >= 75) return '#3b82f6';
    if (score >= 60) return '#f59e0b';
    return '#ef4444';
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#dc2626';
      case 'major': return '#ea580c';
      case 'minor': return '#f59e0b';
      case 'improvement': return '#10b981';
      default: return '#6b7280';
    }
  };

  if (!comparisonId) {
    return (
      <div className="release-decision-page">
        <div className="empty-state">
          <div className="empty-icon">🎯</div>
          <h2>No Comparison Selected</h2>
          <p>Run a comparison first to view release decision</p>
          <button 
            className="btn btn-primary"
            onClick={() => window.location.href = '/compare'}
          >
            Go to Compare Runs
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="release-decision-page">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading comparison results...</p>
        </div>
      </div>
    );
  }

  if (!comparison) {
    return (
      <div className="release-decision-page">
        <div className="alert alert-error">
          {error || 'Comparison not found'}
        </div>
      </div>
    );
  }

  return (
    <div className="release-decision-page">
      <div className="page-header">
        <h1>🎯 Release Decision</h1>
        <p>Comparison ID: {comparisonId}</p>
      </div>

      {/* Verdict Banner */}
      <div 
        className="verdict-banner"
        style={{ 
          background: getVerdictColor(comparison.verdict),
          color: 'white'
        }}
      >
        <div className="verdict-content">
          <div className="verdict-title">{getVerdictText(comparison.verdict)}</div>
          <div className="verdict-score">
            Overall Score: {comparison.overall_score?.toFixed(1)}/100
          </div>
        </div>
      </div>

      {/* Score Dashboard */}
      <div className="score-dashboard">
        <div className="score-card">
          <div className="score-icon">🔧</div>
          <div className="score-info">
            <div className="score-label">Backend Performance</div>
            <div 
              className="score-value"
              style={{ color: getScoreColor(comparison.backend_score) }}
            >
              {comparison.backend_score?.toFixed(1)}
            </div>
          </div>
        </div>

        <div className="score-card">
          <div className="score-icon">⚡</div>
          <div className="score-info">
            <div className="score-label">Frontend UX</div>
            <div 
              className="score-value"
              style={{ color: getScoreColor(comparison.frontend_score) }}
            >
              {comparison.frontend_score?.toFixed(1)}
            </div>
          </div>
        </div>

        <div className="score-card">
          <div className="score-icon">🛡️</div>
          <div className="score-info">
            <div className="score-label">Reliability</div>
            <div 
              className="score-value"
              style={{ color: getScoreColor(comparison.reliability_score) }}
            >
              {comparison.reliability_score?.toFixed(1)}
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Summary */}
      <div className="metrics-overview">
        <div className="metric-box regression">
          <div className="metric-number">{comparison.regression_count}</div>
          <div className="metric-label">Regressions Detected</div>
        </div>
        <div className="metric-box improvement">
          <div className="metric-number">{comparison.improvement_count}</div>
          <div className="metric-label">Improvements</div>
        </div>
        <div className="metric-box stable">
          <div className="metric-number">{comparison.stable_count}</div>
          <div className="metric-label">Stable Metrics</div>
        </div>
      </div>

      {/* Executive Summary */}
      {comparison.summary_text && (
        <div className="executive-summary">
          <h2>Executive Summary</h2>
          <div className="summary-content">
            <pre>{comparison.summary_text}</pre>
          </div>
        </div>
      )}

      {/* Regression Details */}
      <div className="regressions-section">
        <div className="section-header">
          <h2>Detailed Analysis</h2>
          <div className="filters">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
            >
              <option value="all">All Categories</option>
              <option value="jmeter">JMeter (Backend)</option>
              <option value="lighthouse">Lighthouse (Frontend)</option>
            </select>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="major">Major</option>
              <option value="minor">Minor</option>
              <option value="improvement">Improvements</option>
            </select>
          </div>
        </div>

        {regressions.length === 0 ? (
          <div className="no-results">
            <p>No regressions found with selected filters</p>
          </div>
        ) : (
          <div className="regressions-table">
            <table>
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Category</th>
                  <th>Metric</th>
                  <th>Transaction/Page</th>
                  <th>Baseline</th>
                  <th>Current</th>
                  <th>Change</th>
                </tr>
              </thead>
              <tbody>
                {regressions.map((reg, index) => (
                  <tr key={index}>
                    <td>
                      <span 
                        className="severity-badge"
                        style={{ 
                          background: getSeverityColor(reg.severity),
                          color: 'white'
                        }}
                      >
                        {reg.severity}
                      </span>
                    </td>
                    <td className="category-cell">{reg.category}</td>
                    <td className="metric-cell">{reg.metric_name}</td>
                    <td className="transaction-cell">{reg.transaction_name || '-'}</td>
                    <td className="value-cell">{reg.baseline_value?.toFixed(2)}</td>
                    <td className="value-cell">{reg.current_value?.toFixed(2)}</td>
                    <td 
                      className="change-cell"
                      style={{ 
                        color: reg.change_percent > 0 && reg.change_type === 'regression' 
                          ? '#ef4444' 
                          : '#10b981'
                      }}
                    >
                      {reg.change_percent > 0 ? '+' : ''}{reg.change_percent?.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReleaseDecisionPage;
