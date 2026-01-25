import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import FileUpload from '../components/FileUpload';
import { listRuns, RunInfo, generateRunReport, getRunReport, deleteRun, UploadedFile, getReportProgress, ReportProgress } from '../services/api';
import './JMeterPage.css';

interface ProgressState {
  runId: string;
  stage: 'analyzing' | 'generating' | 'completed';
  message: string;
  progress?: ReportProgress;
}

interface ModalContent {
  type: 'html' | 'pdf' | 'ppt';
  content?: string;
  url?: string;
  filename: string;
}

const JMeterPage: React.FC = () => {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<RunInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState<ProgressState | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState<ModalContent | null>(null);
  const [expandedRuns, setExpandedRuns] = useState<Set<string>>(new Set());
  const [recentUploads, setRecentUploads] = useState<UploadedFile[]>([]);
  const progressPollInterval = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadRuns();
    
    return () => {
      if (progressPollInterval.current) {
        clearInterval(progressPollInterval.current);
      }
    };
  }, []);

  const loadRuns = async () => {
    setLoading(true);
    try {
      const result = await listRuns();
      // Filter only JMeter runs
      const jmeterRuns = result.runs.filter(run => run.categories.includes('jmeter'));
      setRuns(jmeterRuns);
    } catch (error) {
      console.error('Failed to load runs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilesUploaded = (files: UploadedFile[]) => {
    setRecentUploads(files);
    loadRuns();
  };

  const toggleExpand = (runId: string) => {
    setExpandedRuns(prev => {
      const next = new Set(prev);
      if (next.has(runId)) {
        next.delete(runId);
      } else {
        next.add(runId);
      }
      return next;
    });
  };

  const handleGenerateReport = async (run: RunInfo, regenerate: boolean = false) => {
    try {
      if (!regenerate) {
        setProgress({
          runId: run.run_id,
          stage: 'analyzing',
          message: 'Report Analysis is in Progress...'
        });

        setRuns(runs =>
          runs.map(r =>
            r.run_id === run.run_id
              ? { ...r, report_status: 'analyzing' }
              : r
          )
        );
      } else {
        setProgress({
          runId: run.run_id,
          stage: 'generating',
          message: 'Regenerating reports with latest engine...'
        });
      }

      const pollProgress = async () => {
        try {
          const progressData = await getReportProgress(run.run_id);
          if (progressData && progressData.status === 'in_progress') {
            setProgress({
              runId: run.run_id,
              stage: progressData.current_task === 'html_generation' ? 'generating' : 'analyzing',
              message: progressData.message || 'Processing...',
              progress: progressData
            });
          } else if (progressData && progressData.status === 'completed') {
            setProgress({
              runId: run.run_id,
              stage: 'completed',
              message: 'Report generation completed!',
              progress: progressData
            });
            clearInterval(progressPollInterval.current!);
            loadRuns();
          } else if (progressData && progressData.status === 'failed') {
            setProgress({
              runId: run.run_id,
              stage: 'completed',
              message: `Error: ${progressData.message || 'Report generation failed'}`,
              progress: progressData
            });
            clearInterval(progressPollInterval.current!);
            loadRuns();
          }
        } catch (error) {
          console.error('Error polling progress:', error);
        }
      };

      if (progressPollInterval.current) {
        clearInterval(progressPollInterval.current);
      }
      progressPollInterval.current = setInterval(pollProgress, 2000);

      await generateRunReport(run.run_id, regenerate);
      await pollProgress();
    } catch (error: any) {
      console.error('Error generating report:', error);
      alert(`Failed to generate report: ${error.response?.data?.detail || error.message}`);
      setProgress(null);
      if (progressPollInterval.current) {
        clearInterval(progressPollInterval.current);
      }
      loadRuns();
    }
  };

  const handleViewReport = async (run: RunInfo, type: 'html' | 'pdf' | 'ppt') => {
    try {
      const report = await getRunReport(run.run_id, type);
      if (type === 'html' && typeof report === 'string') {
        setModalContent({
          type: 'html',
          content: report,
          filename: `${run.run_id}_report.html`
        });
        setModalOpen(true);
      } else if (type === 'pdf' || type === 'ppt') {
        const blob = new Blob([report as Blob], { type: type === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.presentationml.presentation' });
        const url = URL.createObjectURL(blob);
        setModalContent({
          type,
          url,
          filename: `${run.run_id}_report.${type === 'pdf' ? 'pdf' : 'pptx'}`
        });
        setModalOpen(true);
      }
    } catch (error: any) {
      console.error('Error loading report:', error);
      alert(`Failed to load report: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleDeleteRun = async (runId: string) => {
    if (!window.confirm('Are you sure you want to delete this run and all its files?')) {
      return;
    }

    try {
      await deleteRun(runId);
      loadRuns();
    } catch (error: any) {
      console.error('Error deleting run:', error);
      alert(`Failed to delete run: ${error.response?.data?.detail || error.message}`);
    }
  };

  const closeModal = () => {
    setModalOpen(false);
    if (modalContent?.url) {
      URL.revokeObjectURL(modalContent.url);
    }
    setModalContent(null);
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { label: string; class: string }> = {
      'generated': { label: 'Generated', class: 'status-success' },
      'generating': { label: 'Generating', class: 'status-processing' },
      'analyzing': { label: 'Analyzing', class: 'status-processing' },
      'error': { label: 'Error', class: 'status-error' },
      'pending': { label: 'Pending', class: 'status-pending' }
    };
    return statusConfig[status] || { label: status, class: 'status-pending' };
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined });
  };

  const filteredRuns = runs;

  if (loading) {
    return (
      <div className="jmeter-page">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading test runs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="jmeter-page">
      {/* Main Content */}
      <div className="page-content-wrapper">
        {/* Page Header */}
        <div className="page-header">
          <div className="header-content">
            <h1>JMeter Test Results</h1>
            <div className="header-actions">
              <button className="btn-primary" onClick={loadRuns}>
                ↻ Refresh
              </button>
            </div>
          </div>
        </div>
        {/* Main Content Area */}
        <div className="page-main-content">
          {/* Upload Section */}
          <div className="content-section">
            <div className="section-header">
              <h2>Upload Test Results</h2>
            </div>
            <FileUpload 
              onFilesUploaded={handleFilesUploaded}
              defaultCategory="jmeter"
            />
          </div>

          {/* Progress Indicator */}
          {progress && (
            <div className="progress-banner">
              <div className="progress-content">
                <span className="progress-icon">
                  {progress.stage === 'analyzing' && '🔍'}
                  {progress.stage === 'generating' && '⚙️'}
                  {progress.stage === 'completed' && '✅'}
                </span>
                <div className="progress-text">
                  <strong>{progress.message}</strong>
                  {progress.progress && progress.progress.overall_progress !== undefined && (
                    <span className="progress-percent"> - {progress.progress.overall_progress}%</span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Test Runs Table */}
          <div className="content-section">
            <div className="section-header">
              <h2>Recent Test Runs</h2>
            </div>

            {filteredRuns.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">📊</div>
                <h3>No test runs found</h3>
                <p>Upload JMeter JTL or CSV files to get started</p>
              </div>
            ) : (
              <div className="table-container">
                <table className="runs-table">
                  <thead>
                    <tr>
                      <th>Run ID</th>
                      <th>Files</th>
                      <th>Samples</th>
                      <th>Size</th>
                      <th>Uploaded</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRuns.map(run => {
                      const statusBadge = getStatusBadge(run.report_status);
                      return (
                        <tr key={run.run_id} className={expandedRuns.has(run.run_id) ? 'expanded' : ''}>
                          <td className="run-id-cell">
                            <button 
                              className="expand-toggle"
                              onClick={() => toggleExpand(run.run_id)}
                            >
                              {expandedRuns.has(run.run_id) ? '▼' : '▶'}
                            </button>
                            <span className="run-id">{run.run_id}</span>
                          </td>
                          <td>{run.file_count}</td>
                          <td>{run.total_records.toLocaleString()}</td>
                          <td>{(run.total_size / 1024 / 1024).toFixed(2)} MB</td>
                          <td>{formatDate(run.uploaded_at)}</td>
                          <td>
                            <span className={`status-badge ${statusBadge.class}`}>
                              {statusBadge.label}
                            </span>
                          </td>
                          <td>
                            <div className="action-buttons">
                              {run.report_status === 'generated' ? (
                                <>
                                  <button 
                                    onClick={() => handleViewReport(run, 'html')}
                                    className="btn-link"
                                    title="View HTML Report"
                                  >
                                    HTML
                                  </button>
                                  <button 
                                    onClick={() => handleGenerateReport(run, true)}
                                    className="btn-link"
                                    title="Regenerate Report"
                                  >
                                    Regenerate
                                  </button>
                                </>
                              ) : (
                                <button
                                  onClick={() => handleGenerateReport(run, false)}
                                  disabled={run.report_status === 'analyzing' || run.report_status === 'generating'}
                                  className="btn-link btn-primary-link"
                                  title="Generate Report"
                                >
                                  Generate
                                </button>
                              )}
                              <button 
                                onClick={() => handleDeleteRun(run.run_id)}
                                className="btn-link btn-danger-link"
                                title="Delete Run"
                              >
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Expanded File Details */}
            {filteredRuns.map(run => 
              expandedRuns.has(run.run_id) && (
                <div key={`details-${run.run_id}`} className="expanded-details">
                  <div className="details-header">
                    <h3>Files in Run: {run.run_id}</h3>
                  </div>
                  <table className="files-table">
                    <thead>
                      <tr>
                        <th>Filename</th>
                        <th>Category</th>
                        <th>Size</th>
                        <th>Records</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {run.files.map(file => (
                        <tr key={file.file_id}>
                          <td className="file-name">{file.filename}</td>
                          <td><span className="category-tag">{file.category}</span></td>
                          <td>{(file.file_size / 1024).toFixed(2)} KB</td>
                          <td>{file.record_count.toLocaleString()}</td>
                          <td>
                            <span className={`status-badge ${getStatusBadge(file.report_status).class}`}>
                              {getStatusBadge(file.report_status).label}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            )}
          </div>
        </div>
      </div>

      {/* Modal */}
      {modalOpen && modalContent && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{modalContent.filename}</h3>
              <button onClick={closeModal} className="modal-close">×</button>
            </div>
            <div className="modal-body">
              {modalContent.type === 'html' && modalContent.content && (
                <iframe
                  srcDoc={modalContent.content}
                  style={{ width: '100%', height: '80vh', border: 'none' }}
                  title={modalContent.filename}
                />
              )}
              {(modalContent.type === 'pdf' || modalContent.type === 'ppt') && modalContent.url && (
                <iframe
                  src={modalContent.url}
                  style={{ width: '100%', height: '80vh', border: 'none' }}
                  title={modalContent.filename}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default JMeterPage;
