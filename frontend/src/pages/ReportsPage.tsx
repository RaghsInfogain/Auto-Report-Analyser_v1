import React, { useState, useEffect } from 'react';
import { generateReport, generateHTMLReport } from '../services/api';
import './ReportsPage.css';

interface AnalyzedFile {
  file_id: string;
  filename: string;
  category: string;
  metrics: any;
}

interface ReportEntry {
  report_id: string;
  file_id: string;
  filename: string;
  category: string;
  report_type: string;
  generated_at: string;
}

const ReportsPage: React.FC = () => {
  const [analyzedFiles, setAnalyzedFiles] = useState<Record<string, AnalyzedFile>>({});
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  
  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState<{
    type: 'html' | 'pdf' | 'ppt' | 'json';
    content: string | any;
    url?: string;
  } | null>(null);

  useEffect(() => {
    // Load analyzed files from localStorage
    const storedResults = localStorage.getItem('analysisResults');
    if (storedResults) {
      try {
        const parsed = JSON.parse(storedResults);
        setAnalyzedFiles(parsed);
      } catch (error) {
        console.error('Error parsing stored results:', error);
      }
    }
  }, []);

  const handleFileSelection = (fileId: string) => {
    setSelectedFiles(prev => {
      if (prev.includes(fileId)) {
        return prev.filter(id => id !== fileId);
      } else {
        return [...prev, fileId];
      }
    });
  };

  const openModal = (type: 'html' | 'pdf' | 'ppt' | 'json', content: string | any, url?: string) => {
    setModalContent({ type, content, url });
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    // Clean up URL if it exists
    if (modalContent?.url) {
      window.URL.revokeObjectURL(modalContent.url);
    }
    setModalContent(null);
  };

  const handleGenerateReport = async (type: 'json' | 'html' | 'pdf' | 'ppt') => {
    if (selectedFiles.length === 0) {
      alert('Please select analyzed files to generate report');
      return;
    }

    setLoading(true);

    try {
      // Prepare analysis data from selected files
      const selectedAnalysisData: Record<string, any> = {};
      selectedFiles.forEach(fileId => {
        if (analyzedFiles[fileId]) {
          selectedAnalysisData[fileId] = analyzedFiles[fileId];
        }
      });

      if (type === 'html') {
        const htmlContent = await generateHTMLReport(selectedFiles, selectedAnalysisData);
        openModal('html', htmlContent);
      } else if (type === 'pdf') {
        // Call PDF generation endpoint
        const response = await fetch('http://localhost:8000/api/report/generate-pdf', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            file_ids: selectedFiles,
            analysis_data: selectedAnalysisData
          })
        });

        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          openModal('pdf', '', url);
        } else {
          throw new Error('PDF generation failed');
        }
      } else if (type === 'ppt') {
        // Call PPT generation endpoint
        const response = await fetch('http://localhost:8000/api/report/generate-ppt', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            file_ids: selectedFiles,
            analysis_data: selectedAnalysisData
          })
        });

        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          openModal('ppt', '', url);
        } else {
          throw new Error('PPT generation failed');
        }
      } else {
        const result = await generateReport(selectedFiles, selectedAnalysisData);
        openModal('json', result);
      }
    } catch (error: any) {
      console.error('Report generation error:', error);
      alert(`Report generation failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!modalContent) return;

    const timestamp = new Date().toISOString().split('T')[0];
    
    if (modalContent.type === 'pdf' && modalContent.url) {
      const a = document.createElement('a');
      a.href = modalContent.url;
      a.download = `performance_report_${timestamp}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } else if (modalContent.type === 'ppt' && modalContent.url) {
      const a = document.createElement('a');
      a.href = modalContent.url;
      a.download = `performance_report_${timestamp}.pptx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } else if (modalContent.type === 'html') {
      const blob = new Blob([modalContent.content], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `performance_report_${timestamp}.html`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } else if (modalContent.type === 'json') {
      const blob = new Blob([JSON.stringify(modalContent.content, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `performance_report_${timestamp}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    }
  };

  const handleDeleteFile = (fileId: string) => {
    if (window.confirm('Are you sure you want to delete this file and its analysis?')) {
      // Remove from localStorage
      const updatedFiles = { ...analyzedFiles };
      delete updatedFiles[fileId];
      setAnalyzedFiles(updatedFiles);
      localStorage.setItem('analysisResults', JSON.stringify(updatedFiles));

      // Remove from selected files
      setSelectedFiles(prev => prev.filter(id => id !== fileId));

      alert('File deleted successfully!');
    }
  };

  return (
    <div className="reports-page">
      <h1>📊 Reports Management</h1>

      <div className="reports-sections">
        {/* File Selection Section */}
        <div className="file-selection-section">
          <h2>Select Files for Report Generation</h2>
          <p className="section-description">
            Choose analyzed files to include in your performance report.
            Selected: <strong>{selectedFiles.length}</strong> file(s)
          </p>

          {Object.keys(analyzedFiles).length === 0 ? (
            <div className="empty-state">
              <p>📁 No analyzed files available</p>
              <p>Please analyze some files first from the Analysis page</p>
            </div>
          ) : (
            <table className="reports-table">
              <thead>
                <tr>
                  <th>
                    <input
                      type="checkbox"
                      className="table-checkbox"
                      checked={selectedFiles.length === Object.keys(analyzedFiles).length}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedFiles(Object.keys(analyzedFiles));
                        } else {
                          setSelectedFiles([]);
                        }
                      }}
                    />
                  </th>
                  <th>S.No.</th>
                  <th>File Name</th>
                  <th>Type</th>
                  <th>Grade</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(analyzedFiles).map(([fileId, file], index) => {
                  const grade = file.metrics?.summary?.overall_grade || 'N/A';
                  const score = file.metrics?.summary?.overall_score || 0;

                  return (
                    <tr key={fileId} className={selectedFiles.includes(fileId) ? 'selected-row' : ''}>
                      <td>
                        <input
                          type="checkbox"
                          className="table-checkbox"
                          checked={selectedFiles.includes(fileId)}
                          onChange={() => handleFileSelection(fileId)}
                        />
                      </td>
                      <td>{index + 1}</td>
                      <td className="file-name-cell">{file.filename}</td>
                      <td>
                        <span className={`file-type-cell ${file.category}`}>
                          {file.category === 'web_vitals' ? 'Web Vitals' : 
                           file.category === 'jmeter' ? 'JMeter' : 
                           'UI Performance'}
                        </span>
                      </td>
                      <td>
                        {file.category === 'jmeter' ? (
                          <span className={`grade-badge ${grade.replace('+', '')}`}>
                            {grade} ({score}%)
                          </span>
                        ) : (
                          <span className="grade-badge">-</span>
                        )}
                      </td>
                      <td>
                        <button 
                          className="delete-btn"
                          onClick={() => handleDeleteFile(fileId)}
                          title="Delete file and analysis"
                        >
                          🗑️ Delete
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Report Generation Section */}
        {selectedFiles.length > 0 && (
          <div className="report-generation-section">
            <h2>Generate Report</h2>
            <p className="section-description">
              Generate comprehensive reports in your preferred format. Reports will open in a full-screen viewer.
            </p>
            <div className="report-actions">
              <button
                onClick={() => handleGenerateReport('html')}
                disabled={loading}
                className="report-btn html-btn"
              >
                📄 HTML Report
              </button>
              <button
                onClick={() => handleGenerateReport('pdf')}
                disabled={loading}
                className="report-btn pdf-btn"
              >
                📕 PDF Report
              </button>
              <button
                onClick={() => handleGenerateReport('ppt')}
                disabled={loading}
                className="report-btn ppt-btn"
              >
                📊 PowerPoint
              </button>
              <button
                onClick={() => handleGenerateReport('json')}
                disabled={loading}
                className="report-btn json-btn"
              >
                📋 JSON Report
              </button>
            </div>
            {loading && (
              <div className="loading-spinner">
                <div className="spinner"></div>
                <p>Generating report...</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Full-Screen Modal */}
      {modalOpen && modalContent && (
        <div className="report-modal-overlay" onClick={closeModal}>
          <div className="report-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-section">
                <button onClick={closeModal} className="back-modal-btn" title="Back to Reports">
                  ← Back
                </button>
                <h2>
                  {modalContent.type === 'html' && '📄 HTML Report'}
                  {modalContent.type === 'pdf' && '📕 PDF Report'}
                  {modalContent.type === 'ppt' && '📊 PowerPoint Report'}
                  {modalContent.type === 'json' && '📋 JSON Report'}
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
              {modalContent.type === 'html' && (
                <iframe
                  title="HTML Performance Report"
                  srcDoc={modalContent.content}
                  className="modal-iframe"
                />
              )}
              {modalContent.type === 'pdf' && modalContent.url && (
                <iframe
                  title="PDF Performance Report"
                  src={modalContent.url}
                  className="modal-iframe"
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
              {modalContent.type === 'json' && (
                <pre className="json-modal-content">
                  {JSON.stringify(modalContent.content, null, 2)}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportsPage;
