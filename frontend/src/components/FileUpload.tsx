import React, { useState } from 'react';
import { uploadFiles, UploadedFile } from '../services/api';

interface FileUploadProps {
  onFilesUploaded: (files: UploadedFile[]) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFilesUploaded }) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setSelectedFiles(files);
    setCategories(files.map(() => 'web_vitals')); // Default category
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

    setUploading(true);
    try {
      console.log('Starting upload...', { files: selectedFiles.map(f => f.name), categories });
      const result = await uploadFiles(selectedFiles, categories);
      console.log('Upload successful:', result);
      onFilesUploaded(result.files);
      setSelectedFiles([]);
      setCategories([]);
      alert('Files uploaded successfully!');
    } catch (error: any) {
      console.error('Upload error:', error);
      console.error('Error details:', {
        message: error.message,
        response: error.response,
        config: error.config
      });
      const errorMessage = error.response?.data?.detail || error.message || 'Network error';
      alert(`Upload failed: ${errorMessage}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', marginBottom: '20px' }}>
      <h2>Upload Performance Data Files</h2>
      <input
        type="file"
        multiple
        onChange={handleFileSelect}
        style={{ marginBottom: '10px' }}
      />
      {selectedFiles.length > 0 && (
        <div>
          <h3>Selected Files:</h3>
          {selectedFiles.map((file, index) => (
            <div key={index} style={{ marginBottom: '10px', padding: '10px', background: '#f5f5f5' }}>
              <p><strong>{file.name}</strong></p>
              <label>
                Category:
                <select
                  value={categories[index] || 'web_vitals'}
                  onChange={(e) => handleCategoryChange(index, e.target.value)}
                  style={{ marginLeft: '10px' }}
                >
                  <option value="web_vitals">Web Vitals</option>
                  <option value="jmeter">JMeter Test Results</option>
                  <option value="ui_performance">UI Performance</option>
                </select>
              </label>
            </div>
          ))}
          <button onClick={handleUpload} disabled={uploading} style={{ padding: '10px 20px', fontSize: '16px' }}>
            {uploading ? 'Uploading...' : 'Upload Files'}
          </button>
        </div>
      )}
    </div>
  );
};

export default FileUpload;











