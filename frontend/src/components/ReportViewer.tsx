import React from 'react';

interface ReportViewerProps {
  report: any;
}

const ReportViewer: React.FC<ReportViewerProps> = ({ report }) => {
  if (!report) {
    return <div>No report available</div>;
  }

  return (
    <div style={{ padding: '20px' }}>
      <h1>Comprehensive Performance Report</h1>
      <p><strong>Report ID:</strong> {report.report_id}</p>
      <p><strong>Generated At:</strong> {report.generated_at}</p>
      
      {report.sections?.map((section: any, index: number) => (
        <div key={index} style={{ marginTop: '30px', padding: '20px', border: '1px solid #ddd', borderRadius: '8px' }}>
          <h2>{section.title}</h2>
          <pre style={{ background: '#f5f5f5', padding: '15px', overflow: 'auto', maxHeight: '500px' }}>
            {JSON.stringify(section.content, null, 2)}
          </pre>
        </div>
      ))}
    </div>
  );
};

export default ReportViewer;












