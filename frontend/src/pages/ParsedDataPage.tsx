import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getRunParsedData, ParsedDataItem } from '../services/api';
import './ParsedDataPage.css';

const ParsedDataPage: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [parsedData, setParsedData] = useState<ParsedDataItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [runInfo, setRunInfo] = useState<{ run_id: string; total_files: number; parsed_files: number } | null>(null);

  useEffect(() => {
    if (runId) {
      loadParsedData();
    }
  }, [runId]);

  const loadParsedData = async () => {
    if (!runId) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await getRunParsedData(runId);
      setParsedData(response.parsed_data);
      setRunInfo({
        run_id: response.run_id,
        total_files: response.total_files,
        parsed_files: response.parsed_files
      });
    } catch (err: any) {
      console.error('Failed to load parsed data:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load parsed data');
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    } else if (bytes >= 1024) {
      return `${(bytes / 1024).toFixed(2)} KB`;
    }
    return `${bytes} bytes`;
  };

  const getMetricColor = (metric: string, value: number): string => {
    if (metric === 'lcp') {
      if (value <= 2.5) return '#2ecc71'; // green
      if (value <= 4.0) return '#f39c12'; // amber
      return '#e74c3c'; // red
    } else if (metric === 'fcp') {
      if (value <= 1.8) return '#2ecc71';
      if (value <= 3.0) return '#f39c12';
      return '#e74c3c';
    } else if (metric === 'tbt') {
      if (value <= 200) return '#2ecc71';
      if (value <= 600) return '#f39c12';
      return '#e74c3c';
    } else if (metric === 'cls') {
      if (value <= 0.10) return '#2ecc71';
      if (value <= 0.25) return '#f39c12';
      return '#e74c3c';
    }
    return '#34495e';
  };

  if (loading) {
    return (
      <div className="parsed-data-page">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading parsed data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="parsed-data-page">
        <div className="error-container">
          <h2>Error</h2>
          <p>{error}</p>
          <button onClick={() => navigate('/files')} className="btn-primary">
            Back to Files
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="parsed-data-page">
      <div className="page-header">
        <button onClick={() => navigate('/files')} className="btn-back">
          ← Back to Files
        </button>
        <h1>Parsed Data Analysis</h1>
        {runInfo && (
          <div className="run-info">
            <span><strong>Run ID:</strong> {runInfo.run_id}</span>
            <span><strong>Total Files:</strong> {runInfo.total_files}</span>
            <span><strong>Parsed Files:</strong> {runInfo.parsed_files}</span>
          </div>
        )}
      </div>

      {parsedData.length === 0 ? (
        <div className="no-data">
          <p>No parsed data available for this run.</p>
        </div>
      ) : (
        <>
          <div className="data-summary">
            <h2>Data Summary</h2>
            <p>This table shows the raw parsed data from each JSON file. Each row represents one JSON file.</p>
            <p><strong>Total Rows:</strong> {parsedData.length}</p>
          </div>

          <div className="table-container">
            <table className="parsed-data-table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Filename</th>
                  <th>Page Title</th>
                  <th>URL</th>
                  <th>FCP (s)</th>
                  <th>LCP (s)</th>
                  <th>Speed Index (s)</th>
                  <th>TBT (ms)</th>
                  <th>CLS</th>
                  <th>TTI (s)</th>
                  <th>Perf Score</th>
                  <th>Test Duration (s)</th>
                  <th>Elements</th>
                  <th>Bytes</th>
                </tr>
              </thead>
              <tbody>
                {parsedData.map((item, index) => (
                  <tr key={`${item.file_id}-${index}`} className={item.error ? 'error-row' : ''}>
                    <td>{item.run_id}</td>
                    <td className="filename-cell" title={item.file_path}>
                      {item.filename}
                    </td>
                    <td className="title-cell" title={item.page_title}>
                      {item.page_title.length > 30 ? `${item.page_title.substring(0, 30)}...` : item.page_title}
                    </td>
                    <td className="url-cell" title={item.url}>
                      {item.url.length > 40 ? `${item.url.substring(0, 40)}...` : item.url}
                    </td>
                    {item.error ? (
                      <td colSpan={10} className="error-message">
                        Error: {item.error}
                      </td>
                    ) : (
                      <>
                        <td style={{ color: getMetricColor('fcp', item.fcp), fontWeight: 600 }}>
                          {item.fcp.toFixed(2)}
                        </td>
                        <td style={{ color: getMetricColor('lcp', item.lcp), fontWeight: 600 }}>
                          {item.lcp.toFixed(2)}
                        </td>
                        <td>{item.speed_index.toFixed(2)}</td>
                        <td style={{ color: getMetricColor('tbt', item.tbt / 1000), fontWeight: 600 }}>
                          {item.tbt.toFixed(0)}
                        </td>
                        <td style={{ color: getMetricColor('cls', item.cls), fontWeight: 600 }}>
                          {item.cls.toFixed(3)}
                        </td>
                        <td>{item.tti.toFixed(2)}</td>
                        <td>{item.performance_score.toFixed(0)}</td>
                        <td>{item.test_duration.toFixed(2)}</td>
                        <td>{item.total_elements}</td>
                        <td>{formatBytes(item.total_bytes)}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="validation-info">
            <h3>Validation Notes</h3>
            <ul>
              <li>If multiple files belong to the same run, they will have the same <strong>Run ID</strong> but different metrics.</li>
              <li>Each row should have unique values for LCP, FCP, TBT, and other metrics if the JSON files contain different data.</li>
              <li>If you see identical values across multiple rows, it indicates a parsing issue.</li>
              <li>Color coding: <span style={{ color: '#2ecc71' }}>Green</span> = Good, <span style={{ color: '#f39c12' }}>Amber</span> = Needs Improvement, <span style={{ color: '#e74c3c' }}>Red</span> = Poor</li>
            </ul>
          </div>
        </>
      )}
    </div>
  );
};

export default ParsedDataPage;

