import React, { useState, useEffect } from 'react';
import { listFiles, analyzeFiles, UploadedFile, AnalysisResult } from '../services/api';
import AnalysisResults from '../components/AnalysisResults';
import './AnalysisPage.css';

const AnalysisPage: React.FC = () => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [selectedFileIds, setSelectedFileIds] = useState<string[]>([]);
  const [analysisResults, setAnalysisResults] = useState<Record<string, AnalysisResult>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadFiles();
    // Load saved analyses from localStorage
    const savedAnalyses = localStorage.getItem('analysisResults');
    if (savedAnalyses) {
      try {
        setAnalysisResults(JSON.parse(savedAnalyses));
      } catch (error) {
        console.error('Failed to load saved analyses:', error);
      }
    }
  }, []);

  const loadFiles = async () => {
    try {
      const result = await listFiles();
      setUploadedFiles(result.files);
    } catch (error) {
      console.error('Failed to load files:', error);
    }
  };

  const handleAnalyze = async () => {
    if (selectedFileIds.length === 0) {
      alert('Please select files to analyze');
      return;
    }

    setLoading(true);
    try {
      const result = await analyzeFiles(selectedFileIds);
      console.log('Analysis results:', result); // Debug log
      setAnalysisResults(result.results);
      
      // Save to localStorage for persistence
      const existingAnalyses = JSON.parse(localStorage.getItem('analysisResults') || '{}');
      const updatedAnalyses = { ...existingAnalyses, ...result.results };
      localStorage.setItem('analysisResults', JSON.stringify(updatedAnalyses));
      
      alert('Analysis completed successfully! ✅');
    } catch (error: any) {
      console.error('Analysis error:', error);
      alert(`Analysis failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const toggleFileSelection = (fileId: string) => {
    setSelectedFileIds(prev =>
      prev.includes(fileId)
        ? prev.filter(id => id !== fileId)
        : [...prev, fileId]
    );
  };

  return (
    <div className="analysis-page">
      <div className="page-header">
        <h1>Analysis</h1>
        <p>Select files to analyze and view detailed metrics</p>
      </div>

      {uploadedFiles.length > 0 ? (
        <div className="analysis-content">
          <div className="file-selection-panel">
            <h2>Select Files for Analysis</h2>
            <div className="files-list">
              {uploadedFiles.map((file) => (
                <div key={file.file_id} className="file-item">
                  <label className="file-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedFileIds.includes(file.file_id)}
                      onChange={() => toggleFileSelection(file.file_id)}
                    />
                    <div className="file-details">
                      <span className="file-name">{file.filename}</span>
                      <span className="file-category-badge">{file.category}</span>
                    </div>
                  </label>
                </div>
              ))}
            </div>
            <button
              onClick={handleAnalyze}
              disabled={loading || selectedFileIds.length === 0}
              className="analyze-btn"
            >
              {loading ? '⏳ Analyzing...' : '🔍 Analyze Selected Files'}
            </button>
          </div>

          {Object.keys(analysisResults).length > 0 && (
            <div className="results-panel">
              <AnalysisResults results={analysisResults} />
            </div>
          )}
        </div>
      ) : (
        <div className="empty-state">
          <div className="empty-icon">📊</div>
          <h2>No Files Available</h2>
          <p>Upload some files first to start analyzing</p>
          <a href="/upload" className="upload-link-btn">Go to Upload</a>
        </div>
      )}
    </div>
  );
};

export default AnalysisPage;

