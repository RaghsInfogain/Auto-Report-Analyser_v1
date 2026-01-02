import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Debug logging - Version 2.0
console.log('=== API Configuration ===');
console.log('API_BASE_URL:', API_BASE_URL);
console.log('REACT_APP_API_URL env:', process.env.REACT_APP_API_URL);
console.log('Version: 2.0 - Port 8000');
console.log('========================');

const api = axios.create({
  baseURL: API_BASE_URL,
  // Don't set default Content-Type for multipart/form-data
  // Let axios/browser set it automatically with boundary
});

export interface UploadedFile {
  file_id: string;
  filename: string;
  category: string;
  file_path: string;
  file_size: number;
  record_count: number;
  report_status: string; // pending, analyzing, generating, generated, error
  uploaded_at: string;
  has_analysis: boolean;
  has_reports: boolean;
}

export interface AnalysisResult {
  category: string;
  filename: string;
  metrics: any;
}

export const uploadFiles = async (files: File[], categories: string[]): Promise<{ files: UploadedFile[] }> => {
  console.log('API_BASE_URL:', API_BASE_URL);
  console.log('Upload URL:', `${API_BASE_URL}/api/upload`);
  console.log('Files:', files.map(f => ({ name: f.name, size: f.size, type: f.type })));
  console.log('Categories:', categories);
  
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });
  categories.forEach((category) => {
    formData.append('categories', category);
  });

  // Log upload details for debugging
  console.log('Uploading:', {
    fileCount: files.length,
    fileNames: files.map(f => f.name),
    categories: categories
  });

  // Use axios directly - don't set Content-Type, let browser set it with boundary
  const response = await axios.post(`${API_BASE_URL}/api/upload`, formData);
  return response.data;
};

export const listFiles = async (): Promise<{ files: UploadedFile[] }> => {
  const response = await api.get('/api/files');
  return response.data;
};

export const analyzeFiles = async (fileIds: string[]): Promise<{ results: Record<string, AnalysisResult> }> => {
  const response = await api.post('/api/analyze', fileIds);
  return response.data;
};

export const generateReport = async (fileIds: string[], analysisData?: Record<string, any>): Promise<any> => {
  // If we have analysis data from localStorage, send it along
  const requestBody = analysisData ? {
    file_ids: fileIds,
    analysis_data: analysisData
  } : fileIds;
  
  const response = await api.post('/api/report/generate', requestBody);
  return response.data;
};

export const generateHTMLReport = async (fileIds: string[], analysisData?: Record<string, any>): Promise<string> => {
  // If we have analysis data from localStorage, send it along
  const requestBody = analysisData ? {
    file_ids: fileIds,
    analysis_data: analysisData
  } : fileIds;
  
  const response = await api.post('/api/report/generate-html', requestBody, {
    responseType: 'text'
  });
  return response.data;
};

export const generateCompleteReport = async (fileId: string): Promise<{
  success: boolean;
  file_id: string;
  filename: string;
  record_count: number;
  analysis_duration: number;
  report_urls: {
    html: string;
    pdf: string;
    ppt: string;
  };
  report_ids: {
    html: string;
    pdf: string;
    ppt: string;
  };
}> => {
  const response = await api.post(`/api/files/${fileId}/generate-complete-report`);
  return response.data;
};

export const getFileReport = async (fileId: string, reportType: 'html' | 'pdf' | 'ppt'): Promise<Blob | string> => {
  const response = await api.get(`/api/files/${fileId}/reports/${reportType}`, {
    responseType: reportType === 'html' ? 'text' : 'blob'
  });
  return response.data;
};

export const deleteFile = async (fileId: string): Promise<{ message: string }> => {
  const response = await api.delete(`/api/files/${fileId}`);
  return response.data;
};

// Run-based APIs (grouped files from single upload)
export interface RunInfo {
  run_id: string;
  file_count: number;
  total_size: number;
  total_records: number;
  uploaded_at: string;
  report_status: string;
  categories: string[];
  files: UploadedFile[];
}

export const listRuns = async (): Promise<{ runs: RunInfo[] }> => {
  const response = await api.get('/api/runs');
  return response.data;
};

export const getRun = async (runId: string): Promise<RunInfo> => {
  const response = await api.get(`/api/runs/${runId}`);
  return response.data;
};

export const deleteRun = async (runId: string): Promise<{ message: string }> => {
  const response = await api.delete(`/api/runs/${runId}`);
  return response.data;
};

export const generateRunReport = async (runId: string, regenerate: boolean = false): Promise<{
  success: boolean;
  run_id: string;
  file_count: number;
  total_records: number;
  analysis_duration: number;
  report_urls: {
    html: string;
    pdf: string;
    ppt: string;
  };
}> => {
  const response = await api.post(`/api/runs/${runId}/generate-report?regenerate=${regenerate}`);
  return response.data;
};

export const getRunReport = async (runId: string, reportType: 'html' | 'pdf' | 'ppt'): Promise<Blob | string> => {
  const response = await api.get(`/api/runs/${runId}/reports/${reportType}`, {
    responseType: reportType === 'html' ? 'text' : 'blob'
  });
  return response.data;
};

