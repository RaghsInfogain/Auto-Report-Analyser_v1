import React, { useState, useEffect } from 'react';
import FileUpload from '../components/FileUpload';
import { listRuns, RunInfo, generateRunReport, getRunReport, deleteRun, UploadedFile } from '../services/api';
import './FilesPage.css';

interface ProgressState {
  runId: string;
  stage: 'analyzing' | 'generating' | 'completed';
  message: string;
}

interface ModalContent {
  type: 'html' | 'pdf' | 'ppt';
  content?: string;
  url?: string;
  filename: string;
}

const FilesPage: React.FC = () => {
  const [runs, setRuns] = useState<RunInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState<ProgressState | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState<ModalContent | null>(null);
  const [expandedRuns, setExpandedRuns] = useState<Set<string>>(new Set());
  const [recentUploads, setRecentUploads] = useState<UploadedFile[]>([]);

  useEffect(() => {
    loadRuns();
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

      // Call the unified backend endpoint
      const result = await generateRunReport(run.run_id, regenerate);

      // Stage 2: Generating
      setProgress({
        runId: run.run_id,
        stage: 'generating',
        message: 'Report Analysis Completed and Report Generation Started...'
      });

      setRuns(runs =>
        runs.map(r =>
          r.run_id === run.run_id
            ? { ...r, report_status: 'generating', total_records: result.total_records }
            : r
        )
      );

      // Small delay to show the generating message
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Stage 3: Completed
      setProgress({
        runId: run.run_id,
        stage: 'completed',
        message: 'Report generated successfully!'
      });

      setRuns(runs =>
        runs.map(r =>
          r.run_id === run.run_id
            ? { ...r, report_status: 'generated', total_records: result.total_records }
            : r
        )
      );

      // Clear progress after 2 seconds
      setTimeout(() => {
        setProgress(null);
      }, 2000);

    } catch (error: any) {
      console.error('Failed to generate report:', error);
      setProgress({
        runId: run.run_id,
        stage: 'completed',
        message: `Error: ${error.response?.data?.detail || 'Failed to generate report'}`
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
      }, 3000);
    }
  };

  const handleViewReport = async (run: RunInfo, reportType: 'html' | 'pdf' | 'ppt') => {
    try {
      const reportData = await getRunReport(run.run_id, reportType);

      if (reportType === 'html') {
        setModalContent({
          type: 'html',
          content: reportData as string,
          filename: run.run_id
        });
      } else if (reportType === 'pdf') {
        const blob = reportData as Blob;
        const url = URL.createObjectURL(blob);
        setModalContent({
          type: 'pdf',
          url: url,
          filename: run.run_id
        });
      } else if (reportType === 'ppt') {
        const blob = reportData as Blob;
        const url = URL.createObjectURL(blob);
        setModalContent({
          type: 'ppt',
          url: url,
          filename: run.run_id
        });
      }

      setModalOpen(true);
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
      <div className="page-header">
        <h1>📊 My Files</h1>
        <p>Upload files and generate comprehensive performance reports</p>
      </div>

      {/* Upload Section */}
      <div style={{ marginBottom: '2rem', padding: '20px', border: '1px solid #ddd', borderRadius: '8px', background: '#f9f9f9' }}>
        <h2 style={{ marginTop: 0 }}>Upload Performance Data Files</h2>
        <FileUpload onFilesUploaded={handleFilesUploaded} />
        
        {recentUploads.length > 0 && (
          <div style={{ marginTop: '1rem', padding: '1rem', background: '#e8f5e9', borderRadius: '4px' }}>
            <h3 style={{ marginTop: 0 }}>✅ Recently Uploaded</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {recentUploads.map((file) => (
                <div key={file.file_id} style={{ padding: '0.5rem', background: 'white', borderRadius: '4px' }}>
                  <strong>{file.filename}</strong> ({file.category}) - {(file.file_size / 1024).toFixed(2)} KB
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {progress && (
        <div className={`progress-banner ${progress.stage}`}>
          <div className="progress-content">
            <div className="progress-spinner"></div>
            <span className="progress-message">{progress.message}</span>
          </div>
        </div>
      )}

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
                        <div className="report-action">
                          {getStatusBadge('generated')}
                          <button
                            className="generate-btn retry"
                            onClick={() => handleGenerateReport(run, true)}
                            disabled={progress?.runId === run.run_id}
                            title="Regenerate report with latest engine"
                            style={{ marginLeft: '0.5rem', fontSize: '0.85rem', padding: '0.4rem 0.8rem' }}
                          >
                            🔄 Regenerate
                          </button>
                        </div>
                      ) : run.report_status === 'analyzing' || run.report_status === 'generating' ? (
                        getStatusBadge(run.report_status)
                      ) : run.report_status === 'error' ? (
                        <div className="report-action">
                          {getStatusBadge('error')}
                          <button
                            className="generate-btn retry"
                            onClick={() => handleGenerateReport(run)}
                            disabled={progress?.runId === run.run_id}
                          >
                            🔄 Retry
                          </button>
                        </div>
                      ) : (
                        <button
                          className="generate-btn"
                          onClick={() => handleGenerateReport(run)}
                          disabled={progress?.runId === run.run_id}
                        >
                          ⚡ Generate
                        </button>
                      )}
                    </td>
                    <td>
                      {run.report_status === 'generated' ? (
                        <div className="view-buttons">
                          <button
                            className="view-btn html"
                            onClick={() => handleViewReport(run, 'html')}
                            title="View HTML Report"
                          >
                            📄 HTML
                          </button>
                          <button
                            className="view-btn pdf"
                            onClick={() => handleViewReport(run, 'pdf')}
                            title="View PDF Report"
                          >
                            📕 PDF
                          </button>
                          <button
                            className="view-btn ppt"
                            onClick={() => handleViewReport(run, 'ppt')}
                            title="View PowerPoint Report"
                          >
                            📊 PPT
                          </button>
                        </div>
                      ) : (
                        <span className="no-reports">-</span>
                      )}
                    </td>
                    <td>
                      <button
                        className="delete-btn"
                        onClick={() => handleDeleteRun(run)}
                        title="Delete run and all files"
                        disabled={run.report_status === 'analyzing' || run.report_status === 'generating'}
                      >
                        🗑️ Delete
                      </button>
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
