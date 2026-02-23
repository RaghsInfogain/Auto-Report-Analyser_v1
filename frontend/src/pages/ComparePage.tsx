import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import './ComparePage.css';

interface Baseline {
  baseline_id: string;
  run_id: string;
  application: string;
  environment: string;
  version: string;
  baseline_name: string;
}

interface Run {
  run_id: string;
  file_count: number;
  uploaded_at: string;
  categories: string[];
}

interface ComparisonResult {
  comparison_id: string;
  overall_score: number;
  backend_score: number;
  frontend_score: number;
  reliability_score: number;
  verdict: string;
  regression_count: number;
  improvement_count: number;
  stable_count: number;
  status: string;
}

const ComparePage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [baselines, setBaselines] = useState<Baseline[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedBaseline, setSelectedBaseline] = useState('');
  const [selectedRun, setSelectedRun] = useState('');
  const [comparisonType, setComparisonType] = useState('full');
  const [comparing, setComparing] = useState(false);
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchBaselines();
    fetchRuns();
    
    const baselineParam = searchParams.get('baseline');
    if (baselineParam) {
      setSelectedBaseline(baselineParam);
    }
  }, [searchParams]);

  const fetchBaselines = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/comparison/baseline/list?is_active=true');
      const data = await response.json();
      if (data.success) {
        setBaselines(data.baselines || []);
      }
    } catch (err) {
      console.error('Error fetching baselines:', err);
    }
  };

  const fetchRuns = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/runs');
      const data = await response.json();
      if (data.success) {
        setRuns(data.runs || []);
      }
    } catch (err) {
      console.error('Error fetching runs:', err);
    }
  };

  const handleCompare = async () => {
    if (!selectedBaseline || !selectedRun) {
      alert('Please select both baseline and current run');
      return;
    }

    setComparing(true);
    setError('');
    setComparisonResult(null);

    try {
      const response = await fetch('http://localhost:8000/api/comparison/compare', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          baseline_id: selectedBaseline,
          current_run_id: selectedRun,
          comparison_type: comparisonType
        }),
      });

      const data = await response.json();

      if (data.success) {
        const comparisonId = data.comparison_id;
        await pollComparisonStatus(comparisonId);
      } else {
        setError(data.detail || 'Comparison failed');
        setComparing(false);
      }
    } catch (err: any) {
      setError('Error starting comparison: ' + err.message);
      setComparing(false);
      console.error(err);
    }
  };

  const pollComparisonStatus = async (comparisonId: string) => {
    const maxAttempts = 60;
    let attempts = 0;

    const checkStatus = async () => {
      try {
        const response = await fetch(
          `http://localhost:8000/api/comparison/compare/status/${comparisonId}`
        );
        const data = await response.json();

        if (data.status === 'completed') {
          await fetchComparisonResult(comparisonId);
          setComparing(false);
        } else if (data.status === 'failed') {
          setError('Comparison failed: ' + (data.error_message || 'Unknown error'));
          setComparing(false);
        } else if (attempts < maxAttempts) {
          attempts++;
          setTimeout(checkStatus, 2000);
        } else {
          setError('Comparison timed out');
          setComparing(false);
        }
      } catch (err) {
        setError('Error checking comparison status');
        setComparing(false);
      }
    };

    checkStatus();
  };

  const fetchComparisonResult = async (comparisonId: string) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/comparison/compare/result/${comparisonId}`
      );
      const data = await response.json();

      if (data.success) {
        setComparisonResult(data.comparison);
      } else {
        setError('Failed to fetch comparison results');
      }
    } catch (err) {
      setError('Error fetching results');
      console.error(err);
    }
  };

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
      case 'monitor': return '⚠️ Monitor';
      case 'approval_needed': return '⚠️ Approval Needed';
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

  return (
    <div className="compare-page">
      <div className="page-header">
        <div>
          <h1>⚖️ Compare Performance Runs</h1>
          <p>Compare current test results against baseline to detect regressions</p>
        </div>
      </div>

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      <div className="compare-container">
        <div className="compare-form">
          <h2>Select Runs to Compare</h2>
          
          <div className="form-group">
            <label>Baseline Run *</label>
            <select
              value={selectedBaseline}
              onChange={(e) => setSelectedBaseline(e.target.value)}
              disabled={comparing}
            >
              <option value="">Select baseline...</option>
              {baselines.map((baseline) => (
                <option key={baseline.baseline_id} value={baseline.baseline_id}>
                  {baseline.baseline_name} ({baseline.run_id}) - {baseline.environment}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Current Run *</label>
            <select
              value={selectedRun}
              onChange={(e) => setSelectedRun(e.target.value)}
              disabled={comparing}
            >
              <option value="">Select current run...</option>
              {runs.map((run) => (
                <option key={run.run_id} value={run.run_id}>
                  {run.run_id} - {run.file_count} files - {new Date(run.uploaded_at).toLocaleDateString()}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Comparison Type *</label>
            <div className="radio-group">
              <label className="radio-option">
                <input
                  type="radio"
                  value="full"
                  checked={comparisonType === 'full'}
                  onChange={(e) => setComparisonType(e.target.value)}
                  disabled={comparing}
                />
                <span>Full Comparison (Backend + Frontend)</span>
              </label>
              <label className="radio-option">
                <input
                  type="radio"
                  value="jmeter"
                  checked={comparisonType === 'jmeter'}
                  onChange={(e) => setComparisonType(e.target.value)}
                  disabled={comparing}
                />
                <span>JMeter Only (Backend)</span>
              </label>
              <label className="radio-option">
                <input
                  type="radio"
                  value="lighthouse"
                  checked={comparisonType === 'lighthouse'}
                  onChange={(e) => setComparisonType(e.target.value)}
                  disabled={comparing}
                />
                <span>Lighthouse Only (Frontend)</span>
              </label>
            </div>
          </div>

          <button
            className="btn btn-primary btn-large"
            onClick={handleCompare}
            disabled={comparing || !selectedBaseline || !selectedRun}
          >
            {comparing ? 'Comparing...' : 'Run Comparison'}
          </button>
        </div>

        {comparing && (
          <div className="comparing-status">
            <div className="spinner"></div>
            <h3>Analyzing Performance...</h3>
            <p>Comparing metrics, detecting regressions, and calculating release score...</p>
          </div>
        )}

        {comparisonResult && (
          <div className="comparison-results">
            <div className="result-header">
              <h2>Comparison Results</h2>
            </div>

            <div className="score-cards">
              <div className="score-card main-score">
                <div className="score-label">Overall Release Score</div>
                <div 
                  className="score-value"
                  style={{ color: getScoreColor(comparisonResult.overall_score) }}
                >
                  {comparisonResult.overall_score?.toFixed(1) || 0}/100
                </div>
                <div 
                  className="verdict-badge"
                  style={{ 
                    background: getVerdictColor(comparisonResult.verdict),
                    color: 'white'
                  }}
                >
                  {getVerdictText(comparisonResult.verdict)}
                </div>
              </div>

              <div className="score-card">
                <div className="score-label">Backend Performance</div>
                <div 
                  className="score-value"
                  style={{ color: getScoreColor(comparisonResult.backend_score) }}
                >
                  {comparisonResult.backend_score?.toFixed(1) || 0}
                </div>
              </div>

              <div className="score-card">
                <div className="score-label">Frontend UX</div>
                <div 
                  className="score-value"
                  style={{ color: getScoreColor(comparisonResult.frontend_score) }}
                >
                  {comparisonResult.frontend_score?.toFixed(1) || 0}
                </div>
              </div>

              <div className="score-card">
                <div className="score-label">Reliability</div>
                <div 
                  className="score-value"
                  style={{ color: getScoreColor(comparisonResult.reliability_score) }}
                >
                  {comparisonResult.reliability_score?.toFixed(1) || 0}
                </div>
              </div>
            </div>

            <div className="metrics-summary">
              <div className="metric-item regression">
                <span className="metric-count">{comparisonResult.regression_count}</span>
                <span className="metric-label">Regressions</span>
              </div>
              <div className="metric-item improvement">
                <span className="metric-count">{comparisonResult.improvement_count}</span>
                <span className="metric-label">Improvements</span>
              </div>
              <div className="metric-item stable">
                <span className="metric-count">{comparisonResult.stable_count || 0}</span>
                <span className="metric-label">Stable Metrics</span>
              </div>
            </div>

            <div className="result-actions">
              <button 
                className="btn btn-primary"
                onClick={() => window.location.href = `/release-decision?comparison=${comparisonResult.comparison_id}`}
              >
                View Full Release Report
              </button>
              <button 
                className="btn btn-outline"
                onClick={() => setComparisonResult(null)}
              >
                New Comparison
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ComparePage;
