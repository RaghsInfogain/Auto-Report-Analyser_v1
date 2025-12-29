import React from 'react';
import { AnalysisResult } from '../services/api';

interface AnalysisResultsProps {
  results: Record<string, AnalysisResult>;
}

const AnalysisResults: React.FC<AnalysisResultsProps> = ({ results }) => {
  return (
    <div style={{ padding: '20px' }}>
      <h2>Analysis Results</h2>
      {Object.entries(results).map(([fileId, result]) => (
        <div key={fileId} style={{ marginBottom: '30px', padding: '15px', border: '1px solid #ddd', borderRadius: '8px' }}>
          <h3>{result.filename} ({result.category})</h3>
          <div style={{ marginTop: '15px' }}>
            <h4>Metrics:</h4>
            <pre style={{ background: '#f5f5f5', padding: '10px', overflow: 'auto' }}>
              {JSON.stringify(result.metrics, null, 2)}
            </pre>
          </div>
        </div>
      ))}
    </div>
  );
};

export default AnalysisResults;

