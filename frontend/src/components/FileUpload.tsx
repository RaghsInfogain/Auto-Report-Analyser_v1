import React, { useState } from 'react';
import { uploadFiles, UploadedFile } from '../services/api';
import './FileUpload.css';

interface FileUploadProps {
  onFilesUploaded: (files: UploadedFile[]) => void;
  defaultCategory?: string;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFilesUploaded, defaultCategory = 'web_vitals' }) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setSelectedFiles(files);
    setCategories(files.map(() => defaultCategory)); // Use default category
  };

  const handleCategoryChange = (index: number, category: string) => {
    const newCategories = [...categories];
    newCategories[index] = category;
    setCategories(newCategories);
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      alert('Please select files to upload');
      return;
    }

    // Ensure all files have categories
    if (categories.length !== selectedFiles.length) {
      alert(`Please select a category for all ${selectedFiles.length} file(s).`);
      return;
    }

    setUploading(true);
    try {
      console.log('Starting upload...', { files: selectedFiles.map(f => f.name), categories });
      const result = await uploadFiles(selectedFiles, categories);
      console.log('Upload successful:', result);
      onFilesUploaded(result.files);
      setSelectedFiles([]);
      setCategories([]);
      // Reset file input
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
    } catch (error: any) {
      console.error('Upload error:', error);
      console.error('Error details:', {
        message: error.message,
        response: error.response,
        config: error.config
      });
      
      // Handle different error response formats
      let errorMessage = 'Network error';
      
      if (error.response?.data) {
        const errorData = error.response.data;
        
        // Handle FastAPI validation errors (array format)
        if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map((err: any) => {
            if (typeof err === 'string') return err;
            if (err.msg) return err.msg;
            if (err.loc) return `${err.loc.join('.')}: ${err.msg || 'Validation error'}`;
            return JSON.stringify(err);
          }).join(', ');
        }
        // Handle single detail string
        else if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        }
        // Handle object with message
        else if (errorData.message) {
          errorMessage = errorData.message;
        }
        // Fallback to stringify if it's an object
        else if (typeof errorData.detail === 'object') {
          errorMessage = JSON.stringify(errorData.detail);
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      alert(`Upload failed: ${errorMessage}`);
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  return (
    <div className="file-upload-container">
      <div className="upload-area">
        <label className="file-input-label">
          <input
            type="file"
            multiple
            onChange={handleFileSelect}
            className="file-input"
            disabled={uploading}
          />
          <div className="file-input-content">
            <span className="upload-icon">📁</span>
            <span className="upload-text">
              {selectedFiles.length > 0 
                ? `${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''} selected`
                : 'Choose files or drag and drop'}
            </span>
            <span className="upload-hint">JTL, CSV, or JSON files</span>
          </div>
        </label>
      </div>

      {selectedFiles.length > 0 && (
        <div className="selected-files">
          <div className="files-header">
            <h3>Selected Files ({selectedFiles.length})</h3>
            <button 
              className="btn-clear"
              onClick={() => {
                setSelectedFiles([]);
                setCategories([]);
                const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
                if (fileInput) fileInput.value = '';
              }}
            >
              Clear All
            </button>
          </div>
          
          <div className="files-list">
            {selectedFiles.map((file, index) => (
              <div key={index} className="file-item">
                <div className="file-info">
                  <span className="file-icon">📄</span>
                  <div className="file-details">
                    <div className="file-name">{file.name}</div>
                    <div className="file-meta">{formatFileSize(file.size)}</div>
                  </div>
                </div>
                {!defaultCategory && (
                  <select
                    value={categories[index] || 'web_vitals'}
                    onChange={(e) => handleCategoryChange(index, e.target.value)}
                    className="category-select"
                    disabled={uploading}
                  >
                    <option value="web_vitals">Web Vitals</option>
                    <option value="jmeter">JMeter Test Results</option>
                    <option value="ui_performance">UI Performance</option>
                  </select>
                )}
                {defaultCategory && (
                  <div className="category-display">
                    <span className="category-badge">
                      {defaultCategory === 'jmeter' ? 'JMeter Test Results' : 
                       defaultCategory === 'web_vitals' ? 'Web Vitals' : 
                       defaultCategory}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="upload-actions">
            <button 
              onClick={handleUpload} 
              disabled={uploading || selectedFiles.length === 0}
              className="btn-upload"
            >
              {uploading ? (
                <>
                  <span className="spinner-small"></span>
                  Uploading...
                </>
              ) : (
                <>
                  <span>↑</span>
                  Upload Files
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
