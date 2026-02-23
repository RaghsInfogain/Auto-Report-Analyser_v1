import React, { useState, useEffect } from 'react';
import './BaselinesPage.css';

interface Baseline {
  baseline_id: string;
  run_id: string;
  application: string;
  environment: string;
  version: string;
  baseline_name: string;
  description?: string;
  created_at: string;
  created_by: string;
  is_active: boolean;
}

const BaselinesPage: React.FC = () => {
  const [baselines, setBaselines] = useState<Baseline[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [availableRuns, setAvailableRuns] = useState<any[]>([]);
  
  const [newBaseline, setNewBaseline] = useState({
    run_id: '',
    application: '',
    environment: 'production',
    version: '',
    baseline_name: '',
    description: ''
  });

  useEffect(() => {
    fetchBaselines();
    fetchAvailableRuns();
  }, []);

  const fetchBaselines = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/comparison/baseline/list');
      const data = await response.json();
      
      if (data.success) {
        setBaselines(data.baselines || []);
      } else {
        setError('Failed to fetch baselines');
      }
    } catch (err) {
      setError('Error connecting to server');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableRuns = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/runs');
      const data = await response.json();
      
      if (data.success) {
        setAvailableRuns(data.runs || []);
      }
    } catch (err) {
      console.error('Error fetching runs:', err);
    }
  };

  const handleCreateBaseline = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const response = await fetch('http://localhost:8000/api/comparison/baseline/set', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newBaseline),
      });
      
      const data = await response.json();
      
      if (data.success) {
        alert('Baseline created successfully!');
        setShowCreateModal(false);
        setNewBaseline({
          run_id: '',
          application: '',
          environment: 'production',
          version: '',
          baseline_name: '',
          description: ''
        });
        fetchBaselines();
      } else {
        alert('Failed to create baseline: ' + (data.detail || 'Unknown error'));
      }
    } catch (err) {
      alert('Error creating baseline');
      console.error(err);
    }
  };

  const handleDeleteBaseline = async (baselineId: string) => {
    if (!window.confirm('Are you sure you want to delete this baseline?')) {
      return;
    }

    try {
      const response = await fetch(
        `http://localhost:8000/api/comparison/baseline/${baselineId}`,
        { method: 'DELETE' }
      );
      
      const data = await response.json();
      
      if (data.success) {
        alert('Baseline deleted successfully');
        fetchBaselines();
      } else {
        alert('Failed to delete baseline');
      }
    } catch (err) {
      alert('Error deleting baseline');
      console.error(err);
    }
  };

  return (
    <div className="baselines-page">
      <div className="page-header">
        <div>
          <h1>📍 Baseline Manager</h1>
          <p>Manage performance test baselines for comparison</p>
        </div>
        <button 
          className="btn btn-primary"
          onClick={() => setShowCreateModal(true)}
        >
          + Create Baseline
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {loading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading baselines...</p>
        </div>
      ) : baselines.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📍</div>
          <h2>No Baselines Yet</h2>
          <p>Create your first baseline from an existing test run</p>
          <button 
            className="btn btn-primary"
            onClick={() => setShowCreateModal(true)}
          >
            Create First Baseline
          </button>
        </div>
      ) : (
        <div className="baselines-grid">
          {baselines.map((baseline) => (
            <div key={baseline.baseline_id} className="baseline-card">
              <div className="baseline-header">
                <h3>{baseline.baseline_name}</h3>
                {baseline.is_active && <span className="badge badge-success">Active</span>}
              </div>
              
              <div className="baseline-details">
                <div className="detail-row">
                  <span className="label">Application:</span>
                  <span className="value">{baseline.application}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Environment:</span>
                  <span className="value">
                    <span className={`env-badge env-${baseline.environment}`}>
                      {baseline.environment}
                    </span>
                  </span>
                </div>
                <div className="detail-row">
                  <span className="label">Version:</span>
                  <span className="value">{baseline.version}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Run ID:</span>
                  <span className="value">{baseline.run_id}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Created:</span>
                  <span className="value">
                    {new Date(baseline.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>

              {baseline.description && (
                <div className="baseline-description">
                  <p>{baseline.description}</p>
                </div>
              )}

              <div className="baseline-actions">
                <button 
                  className="btn btn-outline"
                  onClick={() => window.location.href = `/compare?baseline=${baseline.baseline_id}`}
                >
                  Compare
                </button>
                <button 
                  className="btn btn-danger"
                  onClick={() => handleDeleteBaseline(baseline.baseline_id)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Create New Baseline</h2>
              <button 
                className="close-btn"
                onClick={() => setShowCreateModal(false)}
              >
                ×
              </button>
            </div>

            <form onSubmit={handleCreateBaseline} className="baseline-form">
              <div className="form-group">
                <label>Run ID *</label>
                <select
                  value={newBaseline.run_id}
                  onChange={(e) => setNewBaseline({ ...newBaseline, run_id: e.target.value })}
                  required
                >
                  <option value="">Select a run...</option>
                  {availableRuns.map((run) => (
                    <option key={run.run_id} value={run.run_id}>
                      {run.run_id} - {run.file_count} files - {new Date(run.uploaded_at).toLocaleDateString()}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Baseline Name *</label>
                <input
                  type="text"
                  value={newBaseline.baseline_name}
                  onChange={(e) => setNewBaseline({ ...newBaseline, baseline_name: e.target.value })}
                  placeholder="e.g., Production Baseline v1.0.0"
                  required
                />
              </div>

              <div className="form-group">
                <label>Application *</label>
                <input
                  type="text"
                  value={newBaseline.application}
                  onChange={(e) => setNewBaseline({ ...newBaseline, application: e.target.value })}
                  placeholder="e.g., MyApp"
                  required
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Environment *</label>
                  <select
                    value={newBaseline.environment}
                    onChange={(e) => setNewBaseline({ ...newBaseline, environment: e.target.value })}
                    required
                  >
                    <option value="development">Development</option>
                    <option value="staging">Staging</option>
                    <option value="production">Production</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Version *</label>
                  <input
                    type="text"
                    value={newBaseline.version}
                    onChange={(e) => setNewBaseline({ ...newBaseline, version: e.target.value })}
                    placeholder="e.g., v1.0.0"
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Description (Optional)</label>
                <textarea
                  value={newBaseline.description}
                  onChange={(e) => setNewBaseline({ ...newBaseline, description: e.target.value })}
                  placeholder="Add notes about this baseline..."
                  rows={3}
                />
              </div>

              <div className="form-actions">
                <button 
                  type="button" 
                  className="btn btn-outline"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create Baseline
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default BaselinesPage;
