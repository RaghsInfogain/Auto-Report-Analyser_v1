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

export interface RunTargets {
  availability_target?: number;
  avg_response_time_target?: number;
  error_rate_target?: number;
  throughput_target?: number;
  p95_target?: number;
  sla_compliance_target?: number;
}

export const getRunTargets = async (runId: string): Promise<{ run_id: string; targets: RunTargets | null }> => {
  const response = await api.get(`/api/runs/${runId}/targets`);
  return response.data;
};

export const saveRunTargets = async (runId: string, targets: RunTargets): Promise<{ run_id: string; targets: any }> => {
  const response = await api.put(`/api/runs/${runId}/targets`, targets);
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

export interface ReportProgress {
  run_id: string;
  status: 'in_progress' | 'completed' | 'failed' | 'stuck' | 'unknown' | 'not_found';
  started_at?: string;
  completed_at?: string;
  current_task?: string;
  tasks: {
    [key: string]: {
      name: string;
      description: string;
      status: 'pending' | 'in_progress' | 'completed' | 'failed';
      started_at?: string;
      completed_at?: string;
      progress_percent: number;
    };
  };
  overall_progress: number;
  message: string;
  last_updated: string;
  can_retry?: boolean;
}

export const getReportProgress = async (runId: string): Promise<ReportProgress> => {
  const response = await api.get(`/api/runs/${runId}/progress`);
  return response.data;
};

export interface ParsedDataItem {
  run_id: string;
  file_id: string;
  filename: string;
  file_path: string;
  page_title: string;
  url: string;
  fcp: number;
  lcp: number;
  speed_index: number;
  tbt: number;
  cls: number;
  tti: number;
  performance_score: number;
  test_duration: number;
  total_elements: number;
  total_bytes: number;
  error?: string;
}

export interface ParsedDataResponse {
  run_id: string;
  total_files: number;
  parsed_files: number;
  parsed_data: ParsedDataItem[];
}

export const getRunParsedData = async (runId: string): Promise<ParsedDataResponse> => {
  const response = await api.get(`/api/runs/${runId}/parsed-data`);
  return response.data;
};

/** Compare two JMeter JTL/CSV files (A = baseline, B = candidate). Returns JSON or HTML string. */
export const compareJmeterAb = async (
  fileA: File,
  fileB: File,
  options?: {
    nameA?: string;
    nameB?: string;
    environmentA?: string;
    environmentB?: string;
    buildA?: string;
    buildB?: string;
    responseFormat?: 'json' | 'html';
    /** Persist HTML + analysis under backend reports/jmeter_compare (same idea as JMeter run reports). */
    persist?: boolean;
  }
): Promise<unknown> => {
  const formData = new FormData();
  formData.append('file_a', fileA);
  formData.append('file_b', fileB);
  if (options?.nameA) formData.append('name_a', options.nameA);
  if (options?.nameB) formData.append('name_b', options.nameB);
  if (options?.environmentA) formData.append('environment_a', options.environmentA);
  if (options?.environmentB) formData.append('environment_b', options.environmentB);
  if (options?.buildA) formData.append('build_a', options.buildA);
  if (options?.buildB) formData.append('build_b', options.buildB);
  const fmt = options?.responseFormat === 'html' ? 'html' : 'json';
  const persist = options?.persist ? 'true' : 'false';
  const response = await axios.post(
    `${API_BASE_URL}/api/jmeter/compare-ab?response_format=${fmt}&persist=${persist}`,
    formData,
    { responseType: fmt === 'html' ? 'text' : 'json' }
  );
  return response.data;
};

/** Compare two existing JMeter runs (merged JTL per run). Opens HTML when responseFormat is html. */
export const compareJmeterAbByRuns = async (
  runIdA: string,
  runIdB: string,
  options?: {
    nameA?: string;
    nameB?: string;
    environmentA?: string;
    environmentB?: string;
    buildA?: string;
    buildB?: string;
    responseFormat?: 'json' | 'html';
    persist?: boolean;
  }
): Promise<unknown> => {
  const formData = new FormData();
  formData.append('run_id_a', runIdA);
  formData.append('run_id_b', runIdB);
  if (options?.nameA) formData.append('name_a', options.nameA);
  if (options?.nameB) formData.append('name_b', options.nameB);
  if (options?.environmentA) formData.append('environment_a', options.environmentA);
  if (options?.environmentB) formData.append('environment_b', options.environmentB);
  if (options?.buildA) formData.append('build_a', options.buildA);
  if (options?.buildB) formData.append('build_b', options.buildB);
  const fmt = options?.responseFormat === 'html' ? 'html' : 'json';
  const persist = options?.persist ? 'true' : 'false';
  const response = await axios.post(
    `${API_BASE_URL}/api/jmeter/compare-ab?response_format=${fmt}&persist=${persist}`,
    formData,
    { responseType: fmt === 'html' ? 'text' : 'json' }
  );
  return response.data;
};

export interface JmeterComparisonReportItem {
  comparison_report_id: string;
  source_type: string;
  run_id_a: string | null;
  run_id_b: string | null;
  name_a: string;
  name_b: string;
  verdict: string | null;
  traffic_signal: string | null;
  file_size: number;
  generated_at: string | null;
  generated_by: string;
  html_url: string;
  download_url: string;
}

export const listJmeterComparisonReports = async (): Promise<{ reports: JmeterComparisonReportItem[] }> => {
  const response = await api.get('/api/jmeter/comparison-reports');
  return response.data;
};

export const regenerateJmeterComparisonReport = async (
  comparisonReportId: string
): Promise<{ success: boolean; comparison_report_id: string; html_url: string }> => {
  const response = await api.post(`/api/jmeter/comparison-reports/${comparisonReportId}/regenerate`);
  return response.data;
};

export const deleteJmeterComparisonReport = async (
  comparisonReportId: string
): Promise<{ success: boolean; comparison_report_id: string }> => {
  const response = await api.delete(`/api/jmeter/comparison-reports/${comparisonReportId}`);
  return response.data;
};

/** Open saved comparison HTML in a new tab (absolute URL). */
export const getJmeterComparisonReportHtmlAbsoluteUrl = (comparisonReportId: string, download?: boolean): string => {
  const q = download ? '?download=1' : '';
  return `${API_BASE_URL}/api/jmeter/comparison-reports/${comparisonReportId}/html${q}`;
};
