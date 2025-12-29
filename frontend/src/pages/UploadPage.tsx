import React, { useState } from 'react';
import FileUpload from '../components/FileUpload';
import { UploadedFile } from '../services/api';
import './UploadPage.css';

const UploadPage: React.FC = () => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);

  const handleFilesUploaded = (files: UploadedFile[]) => {
    setUploadedFiles([...uploadedFiles, ...files]);
  };

  return (
    <div className="upload-page">
      <div className="page-header">
        <h1>Upload Files</h1>
        <p>Upload your performance data files for analysis</p>
      </div>

      <div className="upload-content">
        <FileUpload onFilesUploaded={handleFilesUploaded} />

        {uploadedFiles.length > 0 && (
          <div className="recent-uploads">
            <h2>Recently Uploaded</h2>
            <div className="uploaded-files-list">
              {uploadedFiles.map((file) => (
                <div key={file.file_id} className="uploaded-file-card">
                  <div className="file-icon">📄</div>
                  <div className="file-info">
                    <h3>{file.filename}</h3>
                    <p className="file-category">{file.category}</p>
                    <p className="file-size">{(file.file_size / 1024).toFixed(2)} KB</p>
                  </div>
                  <div className="file-status">✅</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="upload-info">
          <h2>Supported File Types</h2>
          <div className="info-grid">
            <div className="info-card">
              <h3>📊 Web Vitals</h3>
              <p>JSON, CSV files containing Core Web Vitals metrics (LCP, FID, CLS, FCP, TTFB)</p>
            </div>
            <div className="info-card">
              <h3>🧪 JMeter Results</h3>
              <p>JTL, CSV, XML files from JMeter performance tests</p>
            </div>
            <div className="info-card">
              <h3>🎯 UI Performance</h3>
              <p>JSON, CSV files with Navigation Timing API metrics</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UploadPage;












