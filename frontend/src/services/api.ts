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

/**
 * Axios read timeout for run report generation (must stay aligned with
 * backend/app/utils/report_timeouts.py — compute_report_wait_timeout_seconds).
 */
export function reportGenerationTimeoutMs(
  totalBytes?: number,
  totalRecords?: number
): number {
  const MB = 1024 * 1024;
  const mb =
    typeof totalBytes === 'number' && totalBytes > 0 ? totalBytes / MB : 0;
  let sec: number;
  if (mb <= 0) sec = 180;
  else if (mb <= 200) sec = 180 + mb * 0.5;
  else if (mb <= 500) sec = 280 + (mb - 200) * 1.2;
  else {
    sec = 640 + (mb - 500) * 4;
    if (mb > 10_000) {
      sec = Math.max(sec, 7200 + (mb - 10_000) * 0.5);
    }
  }
  const rec =
    typeof totalRecords === 'number' && totalRecords > 0 ? totalRecords : 0;
  if (rec > 2_000_000) {
    sec = Math.max(sec, 400 + rec / 8000);
  }
  sec = Math.min(Math.max(sec, 180), 21600);
  // Extra headroom so the client does not abort before the server budget
  return Math.ceil(sec * 1000) + 120_000;
}

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

export interface UploadBatchResponse {
  message: string;
  run_id: string;
  files: UploadedFile[];
}

const CHUNKED_UPLOAD_THRESHOLD_BYTES = 50 * 1024 * 1024; // 50 MB — use chunked API above this
export const CHUNK_SIZE_BYTES = 32 * 1024 * 1024;

export type UploadProgressCallback = (info: {
  stage: 'upload' | 'finalize';
  fileIndex: number;
  fileCount: number;
  fileName: string;
  percent: number;
  message: string;
}) => void;

export const uploadFiles = async (
  files: File[],
  categories: string[],
  onProgress?: UploadProgressCallback
): Promise<UploadBatchResponse> => {
  const useChunked = files.some((f) => f.size >= CHUNKED_UPLOAD_THRESHOLD_BYTES);
  if (useChunked) {
    return uploadFilesChunked(files, categories, onProgress);
  }

  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  categories.forEach((category) => formData.append('categories', category));

  const response = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
    timeout: 0,
    onUploadProgress: (evt) => {
      if (!onProgress || !evt.total) return;
      const percent = Math.round((evt.loaded / evt.total) * 100);
      onProgress({
        stage: 'upload',
        fileIndex: 0,
        fileCount: files.length,
        fileName: files.length === 1 ? files[0].name : `${files.length} files`,
        percent,
        message: `Uploading… ${(evt.loaded / (1024 * 1024)).toFixed(1)} / ${(evt.total / (1024 * 1024)).toFixed(1)} MB`,
      });
    },
  });
  return response.data;
};

export const uploadFilesChunked = async (
  files: File[],
  categories: string[],
  onProgress?: UploadProgressCallback
): Promise<UploadBatchResponse> => {
  let runId: string | undefined;
  const uploaded: UploadedFile[] = [];

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const category = categories[i];
    const initForm = new FormData();
    initForm.append('filename', file.name);
    initForm.append('category', category);
    initForm.append('total_size', String(file.size));
    if (runId) initForm.append('run_id', runId);

    const initRes = await axios.post(`${API_BASE_URL}/api/upload/init`, initForm, { timeout: 60000 });
    const { upload_id, run_id, chunk_size_recommended } = initRes.data;
    runId = run_id;
    const chunkSize = chunk_size_recommended || CHUNK_SIZE_BYTES;
    const totalChunks = Math.ceil(file.size / chunkSize);

    for (let c = 0; c < totalChunks; c++) {
      const start = c * chunkSize;
      const end = Math.min(start + chunkSize, file.size);
      const blob = file.slice(start, end);
      const chunkForm = new FormData();
      chunkForm.append('upload_id', upload_id);
      chunkForm.append('chunk_index', String(c));
      chunkForm.append('total_chunks', String(totalChunks));
      chunkForm.append('chunk', blob, `${file.name}.part${c}`);

      await axios.post(`${API_BASE_URL}/api/upload/chunk`, chunkForm, {
        timeout: 0,
        maxBodyLength: Infinity,
        maxContentLength: Infinity,
      });

      const pct = Math.round(((c + 1) / totalChunks) * 100);
      onProgress?.({
        stage: 'upload',
        fileIndex: i,
        fileCount: files.length,
        fileName: file.name,
        percent: pct,
        message: `Uploading ${file.name}: part ${c + 1} of ${totalChunks}`,
      });
    }

    const completeForm = new FormData();
    completeForm.append('upload_id', upload_id);
    const completeRes = await axios.post(`${API_BASE_URL}/api/upload/complete`, completeForm, { timeout: 120000 });
    uploaded.push(completeRes.data.file);
  }

  onProgress?.({
    stage: 'finalize',
    fileIndex: files.length - 1,
    fileCount: files.length,
    fileName: '',
    percent: 95,
    message: 'Finalizing run (merge / row estimates)…',
  });

  const finalizeRes = await axios.post(
    `${API_BASE_URL}/api/upload/finalize-run/${runId}`,
    undefined,
    { timeout: 600000 }
  );

  onProgress?.({
    stage: 'finalize',
    fileIndex: files.length - 1,
    fileCount: files.length,
    fileName: '',
    percent: 100,
    message: 'Upload complete',
  });

  return {
    message: finalizeRes.data.message || 'Files uploaded successfully',
    run_id: runId!,
    files: finalizeRes.data.files || uploaded,
  };
};

/** Single run: Lighthouse JSONs + optional custom navigation-timing JSONs (0–many each). */
export const uploadWebVitalsBatch = async (
  lighthouseJsonFiles: File[],
  navigationTimingJsonFiles: File[]
): Promise<UploadBatchResponse> => {
  const files = lighthouseJsonFiles.concat(navigationTimingJsonFiles);
  const categories = files.map(() => 'web_vitals');
  return uploadFiles(files, categories);
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
  files?: UploadedFile[];
  base_url?: string;
}

export const listRuns = async (summary: boolean = true): Promise<{ runs: RunInfo[] }> => {
  const response = await api.get('/api/runs', { params: { summary } });
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
  application_name?: string;
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

/** Start report generation (returns immediately; use waitForRunReportCompletion to poll). */
export const generateRunReport = async (
  runId: string,
  regenerate: boolean = false,
  _totalSizeBytes?: number,
  _totalRecords?: number
): Promise<{
  success: boolean;
  status?: string;
  run_id: string;
  message?: string;
  max_wait_seconds?: number;
  file_count?: number;
  total_records?: number;
  analysis_duration?: number;
  report_urls?: {
    html: string;
    pdf: string;
    ppt: string;
  };
}> => {
  const response = await api.post(
    `/api/runs/${runId}/generate-report?regenerate=${regenerate}`,
    undefined,
    { timeout: 120_000 }
  );
  return response.data;
};

/** Poll until report generation finishes (for large JTL — avoids long-lived HTTP). */
export const waitForRunReportCompletion = async (
  runId: string,
  options?: {
    onProgress?: (progress: ReportProgress) => void;
    totalSizeBytes?: number;
    totalRecords?: number;
    pollIntervalMs?: number;
  }
): Promise<ReportProgress> => {
  const maxWaitMs = reportGenerationTimeoutMs(
    options?.totalSizeBytes,
    options?.totalRecords
  );
  const pollMs = options?.pollIntervalMs ?? 2000;
  const terminal = new Set(['completed', 'failed', 'stuck']);
  const started = Date.now();

  while (Date.now() - started < maxWaitMs) {
    const progress = await getReportProgress(runId);
    options?.onProgress?.(progress);
    if (terminal.has(progress.status)) {
      return progress;
    }
    await new Promise((r) => setTimeout(r, pollMs));
  }

  throw new Error(
    `Report generation timed out after ${Math.round(maxWaitMs / 60000)} minutes. ` +
      'Check server logs — very large files may need more RAM or time.'
  );
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
      status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
      started_at?: string;
      completed_at?: string;
      progress_percent: number;
    };
  };
  overall_progress: number;
  message: string;
  last_updated: string;
  can_retry?: boolean;
  estimated_total_seconds?: number;
  estimated_remaining_seconds?: number;
  elapsed_seconds?: number;
  eta_label?: string;
  html_only?: boolean;
}

export const formatEtaLabel = (progress?: ReportProgress | null): string | undefined => {
  if (!progress) return undefined;
  if (progress.status === 'completed') return 'Complete';
  if (progress.eta_label) return progress.eta_label;
  if (progress.estimated_remaining_seconds != null) {
    const s = progress.estimated_remaining_seconds;
    if (s < 60) return `~${s} sec remaining`;
    if (s < 3600) return `~${Math.max(1, Math.round(s / 60))} min remaining`;
    const h = Math.floor(s / 3600);
    const m = Math.round((s % 3600) / 60);
    return m > 0 ? `~${h}h ${m}m remaining` : `~${h}h remaining`;
  }
  return undefined;
};

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
