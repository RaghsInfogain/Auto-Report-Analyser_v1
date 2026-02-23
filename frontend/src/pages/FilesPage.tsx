import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import FileUpload from '../components/FileUpload';
import { listRuns, RunInfo, generateRunReport, getRunReport, deleteRun, UploadedFile, getReportProgress, ReportProgress } from '../services/api';
import './FilesPage.css';

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

const FilesPage: React.FC = () => {
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
      setRuns(result.runs);
    } catch (error) {
      console.error('Failed to load runs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilesUploaded = (files: UploadedFile[]) => {
    setRecentUploads(files);
    // Reload runs to show newly uploaded files
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
      // Stage 1: Analyzing (skip if regenerating)
      if (!regenerate) {
        setProgress({
          runId: run.run_id,
          stage: 'analyzing',
          message: 'Report Analysis is in Progress...'
        });

        // Update run status in the UI
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

      // Start polling for progress
      const pollProgress = async () => {
        try {
          const progressData = await getReportProgress(run.run_id);
          setProgress(prev => prev ? { ...prev, progress: progressData } : null);
          
          if (progressData.status === 'completed' || progressData.status === 'failed' || progressData.status === 'stuck') {
            if (progressPollInterval.current) {
              clearInterval(progressPollInterval.current);
              progressPollInterval.current = null;
            }
            
            if (progressData.status === 'completed') {
              setProgress({
                runId: run.run_id,
                stage: 'completed',
                message: 'Report generated successfully!',
                progress: progressData
              });
              setRuns(runs =>
                runs.map(r =>
                  r.run_id === run.run_id
                    ? { ...r, report_status: 'generated' }
                    : r
                )
              );
              setTimeout(() => setProgress(null), 3000);
            } else if (progressData.status === 'stuck' || progressData.status === 'failed') {
              setProgress({
                runId: run.run_id,
                stage: 'completed',
                message: progressData.message || 'Report generation failed or was stuck',
                progress: progressData
              });
              setRuns(runs =>
                runs.map(r =>
                  r.run_id === run.run_id
                    ? { ...r, report_status: 'pending' }
                    : r
                )
              );
              setTimeout(() => setProgress(null), 5000);
            }
          }
        } catch (error) {
          console.error('Error polling progress:', error);
        }
      };

      // Poll every 2 seconds
      if (progressPollInterval.current) {
        clearInterval(progressPollInterval.current);
      }
      progressPollInterval.current = setInterval(pollProgress, 2000);

      // Call the unified backend endpoint (this will take time)
      const result = await generateRunReport(run.run_id, regenerate);

      // Stop polling
      if (progressPollInterval.current) {
        clearInterval(progressPollInterval.current);
        progressPollInterval.current = null;
      }

      // Final progress update
      const finalProgress = await getReportProgress(run.run_id);
      setProgress({
        runId: run.run_id,
        stage: 'completed',
        message: 'Report generated successfully!',
        progress: finalProgress
      });

      setRuns(runs =>
        runs.map(r =>
          r.run_id === run.run_id
            ? { ...r, report_status: 'generated', total_records: result.total_records }
            : r
        )
      );

      // Clear progress after 3 seconds
      setTimeout(() => {
        setProgress(null);
      }, 3000);

    } catch (error: any) {
      console.error('Failed to generate report:', error);
      
      // Stop polling on error
      if (progressPollInterval.current) {
        clearInterval(progressPollInterval.current);
        progressPollInterval.current = null;
      }
      
      setProgress({
        runId: run.run_id,
        stage: 'completed',
        message: `Error: ${error.response?.data?.detail || 'Failed to generate report'}`,
        progress: undefined
      });
      setRuns(runs =>
        runs.map(r =>
          r.run_id === run.run_id
            ? { ...r, report_status: 'error' }
            : r
        )
      );
      setTimeout(() => {
        setProgress(null);
      }, 5000);
    }
  };

  const handleViewReport = async (run: RunInfo, reportType: 'html' | 'pdf' | 'ppt') => {
    try {
      const reportData = await getRunReport(run.run_id, reportType);

      if (reportType === 'html') {
        // Open HTML report in a new tab
        const htmlContent = reportData as string;
        const newWindow = window.open('', '_blank');
        if (newWindow) {
          newWindow.document.write(htmlContent);
          newWindow.document.close();
          newWindow.document.title = `${run.run_id} - Performance Report`;
        } else {
          alert('Please allow pop-ups to view the report in a new tab');
        }
      } else if (reportType === 'pdf') {
        const blob = reportData as Blob;
        const url = URL.createObjectURL(blob);
        setModalContent({
          type: 'pdf',
          url: url,
          filename: run.run_id
        });
        setModalOpen(true);
      } else if (reportType === 'ppt') {
        const blob = reportData as Blob;
        const url = URL.createObjectURL(blob);
        setModalContent({
          type: 'ppt',
          url: url,
          filename: run.run_id
        });
        setModalOpen(true);
      }
    } catch (error: any) {
      console.error('Failed to view report:', error);
      alert(`Failed to load ${reportType.toUpperCase()} report: ${error.response?.data?.detail || error.message}`);
    }
  };

  const closeModal = () => {
    if (modalContent?.url) {
      URL.revokeObjectURL(modalContent.url);
    }
    setModalOpen(false);
    setModalContent(null);
  };

  const handleDownload = () => {
    if (!modalContent) return;

    const { type, content, url, filename } = modalContent;

    if (type === 'html' && content) {
      const blob = new Blob([content], { type: 'text/html' });
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `${filename}_report.html`;
      link.click();
      URL.revokeObjectURL(downloadUrl);
    } else if (url) {
      const link = document.createElement('a');
      link.href = url;
      link.download = `${filename}_report.${type === 'pdf' ? 'pdf' : 'pptx'}`;
      link.click();
    }
  };

  const handleDeleteRun = async (run: RunInfo) => {
    if (!window.confirm(`Are you sure you want to delete Run "${run.run_id}"?\n\nThis will delete ${run.file_count} file(s) and all associated reports.`)) {
      return;
    }

    try {
      await deleteRun(run.run_id);
      setRuns(runs => runs.filter(r => r.run_id !== run.run_id));
    } catch (error: any) {
      console.error('Failed to delete run:', error);
      alert(`Failed to delete run: ${error.response?.data?.detail || error.message}`);
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'web_vitals': return '⚡';
      case 'jmeter': return '🧪';
      case 'ui_performance': return '🎯';
      default: return '📄';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending': return <span className="status-badge pending">Pending</span>;
      case 'analyzing': return <span className="status-badge analyzing">Analyzing...</span>;
      case 'generating': return <span className="status-badge generating">Generating...</span>;
      case 'generated': return <span className="status-badge generated">Generated</span>;
      case 'error': return <span className="status-badge error">Error</span>;
      default: return <span className="status-badge pending">Pending</span>;
    }
  };

  const formatRunId = (runId: string) => {
    // Extract the date part if it follows the pattern RUN-YYYYMMDDHHMMSS-xxx
    const match = runId.match(/RUN-(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})-(.+)/);
    if (match) {
      return `RUN-${match[7].toUpperCase()}`;
    }
    return runId.substring(0, 16);
  };

  return (
    <div className="files-page">
      <div className="page-content-wrapper">
        {/* Page Header */}
        <div className="page-header">
          <div className="header-content">
            <h1>My Files</h1>
            <p>Upload files and generate comprehensive performance reports</p>
          </div>
        </div>

        {/* Upload Section */}
        <div className="content-section">
          <div className="section-header">
            <h2>Upload Performance Data Files</h2>
          </div>
          <FileUpload onFilesUploaded={handleFilesUploaded} />
        </div>

      {progress && (
        <div className={`progress-banner ${progress.stage}`}>
          <div className="progress-content">
            <div className="progress-spinner"></div>
            <div className="progress-details">
              <span className="progress-message">{progress.message}</span>
              {progress.progress && (
                <div className="progress-tasks">
                  <div className="progress-bar-container">
                    <div className="progress-bar" style={{ width: `${progress.progress.overall_progress}%` }}></div>
                    <span className="progress-percent">{progress.progress.overall_progress}%</span>
                  </div>
                  <table className="progress-table">
                    <thead>
                      <tr>
                        <th>Status</th>
                        <th>Task</th>
                        <th>Description</th>
                        <th>Progress</th>
                        <th>Started</th>
                        <th>Completed</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(progress.progress.tasks || {}).map(([taskId, task]: [string, any]) => (
                        <tr key={taskId} className={`task-row ${task.status}`}>
                          <td className="task-status-cell">
                            <span className="task-status-icon">
                              {task.status === 'completed' ? '✓' : task.status === 'in_progress' ? '⟳' : task.status === 'failed' ? '✗' : '○'}
                            </span>
                            <span className="task-status-text">{task.status}</span>
                          </td>
                          <td className="task-name-cell">{task.name}</td>
                          <td className="task-description-cell">{task.description || '-'}</td>
                          <td className="task-progress-cell">
                            {task.status === 'in_progress' ? `${task.progress_percent}%` : 
                             task.status === 'completed' ? '100%' : 
                             task.status === 'failed' ? 'Failed' : '0%'}
                          </td>
                          <td className="task-time-cell">
                            {task.started_at ? new Date(task.started_at).toLocaleTimeString() : '-'}
                          </td>
                          <td className="task-time-cell">
                            {task.completed_at ? new Date(task.completed_at).toLocaleTimeString() : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

        {/* Test Runs Table */}
        <div className="content-section">
          <div className="section-header">
            <h2>All Test Runs</h2>
          </div>

          {loading ? (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Loading runs...</p>
            </div>
          ) : runs.length > 0 ? (
            <div className="files-table-container">
          <table className="files-table">
            <thead>
              <tr>
                <th style={{width: '40px'}}></th>
                <th>Run ID</th>
                <th>Files</th>
                <th>Type</th>
                <th>No. Of Records</th>
                <th>Report Status</th>
                <th>View Reports</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run, index) => (
                <React.Fragment key={run.run_id}>
                  <tr className={expandedRuns.has(run.run_id) ? 'expanded-row' : ''}>
                    <td>
                      <button 
                        className="expand-btn"
                        onClick={() => toggleExpand(run.run_id)}
                        title={expandedRuns.has(run.run_id) ? "Collapse" : "Expand to see files"}
                      >
                        {expandedRuns.has(run.run_id) ? '▼' : '▶'}
                      </button>
                    </td>
                    <td>
                      <div className="run-id">
                        {run.categories.map(c => getCategoryIcon(c)).join('')} {formatRunId(run.run_id)}
                      </div>
                    </td>
                    <td>
                      <div className="file-count">
                        {run.file_count} file{run.file_count > 1 ? 's' : ''}
                        <span className="file-size">({(run.total_size / 1024).toFixed(2)} KB)</span>
                      </div>
                    </td>
                    <td>
                      <div className="category-badges">
                        {run.categories.map(cat => (
                          <span key={cat} className="file-type">{cat.replace('_', ' ')}</span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <span className="record-count">
                        {run.total_records > 0 ? run.total_records.toLocaleString() : '-'}
                      </span>
                    </td>
                    <td>
                      {run.report_status === 'generated' ? (
                        <span className="status-badge status-generated">Generated</span>
                      ) : run.report_status === 'analyzing' || run.report_status === 'generating' ? (
                        <span className={`status-badge status-${run.report_status === 'analyzing' ? 'processing' : 'processing'}`}>
                          {run.report_status === 'analyzing' ? 'Analyzing' : 'Generating'}
                        </span>
                      ) : run.report_status === 'error' ? (
                        <span className="status-badge status-error">Error</span>
                      ) : (
                        <button
                          className="btn-link btn-primary-link"
                          onClick={() => handleGenerateReport(run)}
                          disabled={progress?.runId === run.run_id}
                          title="Generate Report"
                        >
                          Generate
                        </button>
                      )}
                    </td>
                    <td>
                      {run.report_status === 'generated' ? (
                        <div className="action-buttons">
                          <button 
                            onClick={() => handleViewReport(run, 'html')}
                            className="btn-link"
                            title="View HTML Report"
                          >
                            HTML
                          </button>
                          <button 
                            onClick={() => handleViewReport(run, 'pdf')}
                            className="btn-link"
                            title="View PDF Report"
                          >
                            PDF
                          </button>
                          <button 
                            onClick={() => handleViewReport(run, 'ppt')}
                            className="btn-link"
                            title="View PowerPoint Report"
                          >
                            PPT
                          </button>
                        </div>
                      ) : (
                        <span style={{ color: '#999', fontSize: '0.875rem' }}>-</span>
                      )}
                    </td>
                    <td>
                      <div className="action-buttons">
                        {run.report_status === 'generated' && (
                          <button 
                            onClick={() => handleGenerateReport(run, true)}
                            className="btn-link"
                            title="Regenerate Report"
                            disabled={progress?.runId === run.run_id}
                          >
                            Regenerate
                          </button>
                        )}
                        {run.categories.includes('web_vitals') && (
                          <button
                            className="btn-link btn-parsed"
                            onClick={() => navigate(`/runs/${run.run_id}/parsed-data`)}
                            title="View parsed data from JSON files"
                          >
                            Parsed Data
                          </button>
                        )}
                        <button 
                          onClick={() => handleDeleteRun(run)}
                          className="btn-link btn-danger-link"
                          title="Delete Run"
                          disabled={run.report_status === 'analyzing' || run.report_status === 'generating'}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expandedRuns.has(run.run_id) && (
                    <tr className="files-detail-row">
                      <td colSpan={8}>
                        <div className="files-detail">
                          <table className="inner-files-table">
                            <thead>
                              <tr>
                                <th>File Name</th>
                                <th>Category</th>
                                <th>Size</th>
                                <th>Records</th>
                              </tr>
                            </thead>
                            <tbody>
                              {run.files.map(file => (
                                <tr key={file.file_id}>
                                  <td>{getCategoryIcon(file.category)} {file.filename}</td>
                                  <td><span className="file-type-small">{file.category.replace('_', ' ')}</span></td>
                                  <td>{(file.file_size / 1024).toFixed(2)} KB</td>
                                  <td>{file.record_count > 0 ? file.record_count.toLocaleString() : '-'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">📁</div>
              <h2>No Runs Found</h2>
              <p>Upload some files above to get started with performance analysis</p>
            </div>
          )}
        </div>
      </div>

      {modalOpen && modalContent && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-window" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-section">
                <button onClick={closeModal} className="back-modal-btn" title="Back to Files">
                  ← Back
                </button>
                <h2>
                  {modalContent.type === 'html' && '📄 HTML Report'}
                  {modalContent.type === 'pdf' && '📕 PDF Report'}
                  {modalContent.type === 'ppt' && '📊 PowerPoint Report'}
                </h2>
              </div>
              <div className="modal-actions">
                <button onClick={handleDownload} className="download-modal-btn" title="Download Report">
                  💾 Download
                </button>
                <button onClick={closeModal} className="close-modal-btn" title="Close">
                  ✕
                </button>
              </div>
            </div>

            <div className="modal-body">
              {modalContent.type === 'html' && modalContent.content && (
                <iframe
                  srcDoc={modalContent.content}
                  title="HTML Report"
                  className="report-iframe"
                />
              )}

              {modalContent.type === 'pdf' && modalContent.url && (
                <iframe
                  src={modalContent.url}
                  title="PDF Report"
                  className="report-iframe"
                />
              )}

              {modalContent.type === 'ppt' && modalContent.url && (
                <div className="ppt-preview">
                  <div className="ppt-icon">📊</div>
                  <h3>PowerPoint Report Generated!</h3>
                  <p>PowerPoint files cannot be previewed in the browser.</p>
                  <p>Click the download button above to save the file.</p>
                  <button onClick={handleDownload} className="download-ppt-btn">
                    💾 Download PowerPoint Report
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FilesPage;
