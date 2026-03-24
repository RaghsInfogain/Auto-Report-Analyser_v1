import React, { useState, useEffect, useCallback } from 'react';
import {
  listRuns,
  RunInfo,
  compareJmeterAb,
  compareJmeterAbByRuns,
  listJmeterComparisonReports,
  regenerateJmeterComparisonReport,
  deleteJmeterComparisonReport,
  getJmeterComparisonReportHtmlAbsoluteUrl,
  JmeterComparisonReportItem,
} from '../services/api';
import './PerformanceTestComparePage.css';

const PerformanceTestComparePage: React.FC = () => {
  const [runs, setRuns] = useState<RunInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [savedReports, setSavedReports] = useState<JmeterComparisonReportItem[]>([]);
  const [savedLoading, setSavedLoading] = useState(true);
  const [compareMode, setCompareMode] = useState<'files' | 'runs'>('runs');
  const [compareFileA, setCompareFileA] = useState<File | null>(null);
  const [compareFileB, setCompareFileB] = useState<File | null>(null);
  const [compareRunIdA, setCompareRunIdA] = useState('');
  const [compareRunIdB, setCompareRunIdB] = useState('');
  const [compareLabelA, setCompareLabelA] = useState('Test A (Baseline)');
  const [compareLabelB, setCompareLabelB] = useState('Test B');
  const [saveToLibrary, setSaveToLibrary] = useState(true);
  const [compareLoading, setCompareLoading] = useState(false);
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);

  const loadSavedReports = useCallback(async () => {
    setSavedLoading(true);
    try {
      const res = await listJmeterComparisonReports();
      setSavedReports(res.reports || []);
    } catch (e) {
      console.error('Failed to load saved comparison reports:', e);
      setSavedReports([]);
    } finally {
      setSavedLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRuns();
    loadSavedReports();
  }, [loadSavedReports]);

  const loadRuns = async () => {
    setLoading(true);
    try {
      const result = await listRuns();
      const jmeterRuns = result.runs.filter((run) => run.categories.includes('jmeter'));
      setRuns(jmeterRuns);
    } catch (error) {
      console.error('Failed to load runs:', error);
    } finally {
      setLoading(false);
    }
  };

  const openComparisonHtmlBlob = (html: string) => {
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener,noreferrer');
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  };

  const handleCompareAb = async () => {
    setCompareLoading(true);
    try {
      const nameA = compareLabelA.trim() || 'Test A (Baseline)';
      const nameB = compareLabelB.trim() || 'Test B';

      if (compareMode === 'files') {
        if (!compareFileA || !compareFileB) {
          alert('Select both JMeter files: baseline (A) and candidate (B).');
          return;
        }
        if (saveToLibrary) {
          const data = (await compareJmeterAb(compareFileA, compareFileB, {
            nameA,
            nameB,
            responseFormat: 'json',
            persist: true,
          })) as { comparison_report_id?: string; saved?: boolean };
          if (!data.comparison_report_id) {
            alert('Report was not saved. Check API response.');
            return;
          }
          window.open(getJmeterComparisonReportHtmlAbsoluteUrl(data.comparison_report_id), '_blank', 'noopener,noreferrer');
          await loadSavedReports();
        } else {
          const html = (await compareJmeterAb(compareFileA, compareFileB, {
            nameA,
            nameB,
            responseFormat: 'html',
            persist: false,
          })) as string;
          if (typeof html !== 'string' || !html.includes('<html')) {
            alert('Unexpected response from comparison API.');
            return;
          }
          openComparisonHtmlBlob(html);
        }
      } else {
        if (!compareRunIdA || !compareRunIdB) {
          alert('Select baseline run (A) and candidate run (B).');
          return;
        }
        if (compareRunIdA === compareRunIdB) {
          alert('Choose two different runs to compare.');
          return;
        }
        if (saveToLibrary) {
          const data = (await compareJmeterAbByRuns(compareRunIdA, compareRunIdB, {
            nameA: compareLabelA.trim() || compareRunIdA,
            nameB: compareLabelB.trim() || compareRunIdB,
            responseFormat: 'json',
            persist: true,
          })) as { comparison_report_id?: string };
          if (!data.comparison_report_id) {
            alert('Report was not saved. Check API response.');
            return;
          }
          window.open(getJmeterComparisonReportHtmlAbsoluteUrl(data.comparison_report_id), '_blank', 'noopener,noreferrer');
          await loadSavedReports();
        } else {
          const html = (await compareJmeterAbByRuns(compareRunIdA, compareRunIdB, {
            nameA: compareLabelA.trim() || compareRunIdA,
            nameB: compareLabelB.trim() || compareRunIdB,
            responseFormat: 'html',
            persist: false,
          })) as string;
          if (typeof html !== 'string' || !html.includes('<html')) {
            alert('Unexpected response from comparison API.');
            return;
          }
          openComparisonHtmlBlob(html);
        }
      }
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      const msg =
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail.map((d: any) => d.msg || d).join('; ')
            : error.message;
      console.error('Compare A/B failed:', error);
      alert(`Comparison failed: ${msg || error.message}`);
    } finally {
      setCompareLoading(false);
    }
  };

  const handleViewSaved = (id: string) => {
    window.open(getJmeterComparisonReportHtmlAbsoluteUrl(id), '_blank', 'noopener,noreferrer');
  };

  const handleDownloadSaved = (id: string) => {
    window.open(getJmeterComparisonReportHtmlAbsoluteUrl(id, true), '_blank', 'noopener,noreferrer');
  };

  const handleRegenerate = async (id: string) => {
    if (!window.confirm('Regenerate this report from stored data (runs re-loaded from DB when possible)?')) return;
    setRegeneratingId(id);
    try {
      await regenerateJmeterComparisonReport(id);
      await loadSavedReports();
      alert('Report regenerated successfully.');
    } catch (error: any) {
      alert(error.response?.data?.detail || error.message || 'Regenerate failed');
    } finally {
      setRegeneratingId(null);
    }
  };

  const handleDeleteSaved = async (id: string) => {
    if (!window.confirm('Delete this saved comparison report?')) return;
    try {
      await deleteJmeterComparisonReport(id);
      await loadSavedReports();
    } catch (error: any) {
      alert(error.response?.data?.detail || error.message || 'Delete failed');
    }
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleString();
  };

  const signalClass = (signal: string | null) => {
    if (signal === 'red') return 'signal-badge signal-red';
    if (signal === 'amber') return 'signal-badge signal-amber';
    return 'signal-badge signal-green';
  };

  if (loading) {
    return (
      <div className="perf-compare-page">
        <div className="loading-container">
          <div className="spinner" />
          <p>Loading JMeter runs…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="perf-compare-page">
      <div className="page-content-wrapper">
        <div className="page-header">
          <div className="header-content">
            <div>
              <h1>Performance test comparison</h1>
              <p className="page-lead">
                Compare two JMeter runs or two result files. Reports can be stored under{' '}
                <code>reports/jmeter_compare</code> like standard JMeter run reports, then opened, downloaded,
                regenerated, or deleted from the list below.
              </p>
            </div>
            <div className="header-buttons">
              <button type="button" className="btn-secondary" onClick={() => { loadRuns(); loadSavedReports(); }}>
                ↻ Refresh all
              </button>
            </div>
          </div>
        </div>

        <div className="page-main-content">
          <div className="content-section">
            <div className="section-header">
              <h2>Build comparison report</h2>
            </div>

            <label className="save-library-toggle">
              <input
                type="checkbox"
                checked={saveToLibrary}
                onChange={(e) => setSaveToLibrary(e.target.checked)}
              />
              <span>
                Save report to library (stored on server like JMeter test reports — enables HTML, download, regenerate,
                delete below)
              </span>
            </label>

            <div className="compare-mode-toggle" role="tablist" aria-label="Comparison source">
              <button
                type="button"
                className={compareMode === 'runs' ? 'active' : ''}
                onClick={() => setCompareMode('runs')}
              >
                Existing runs
              </button>
              <button
                type="button"
                className={compareMode === 'files' ? 'active' : ''}
                onClick={() => setCompareMode('files')}
              >
                Upload two files
              </button>
            </div>

            <div className="compare-labels-row">
              <label>
                <span>Report name for A (baseline)</span>
                <input
                  type="text"
                  value={compareLabelA}
                  onChange={(e) => setCompareLabelA(e.target.value)}
                  placeholder="Test A (Baseline)"
                />
              </label>
              <label>
                <span>Report name for B (candidate)</span>
                <input
                  type="text"
                  value={compareLabelB}
                  onChange={(e) => setCompareLabelB(e.target.value)}
                  placeholder="Test B"
                />
              </label>
            </div>

            {compareMode === 'runs' ? (
              <div className="compare-runs-row">
                <label>
                  <span>Baseline run (A)</span>
                  <select
                    value={compareRunIdA}
                    onChange={(e) => setCompareRunIdA(e.target.value)}
                    disabled={runs.length === 0}
                  >
                    <option value="">Select run…</option>
                    {runs.map((r) => (
                      <option key={`a-${r.run_id}`} value={r.run_id}>
                        {r.run_id} — {r.total_records.toLocaleString()} samples
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Candidate run (B)</span>
                  <select
                    value={compareRunIdB}
                    onChange={(e) => setCompareRunIdB(e.target.value)}
                    disabled={runs.length === 0}
                  >
                    <option value="">Select run…</option>
                    {runs.map((r) => (
                      <option key={`b-${r.run_id}`} value={r.run_id}>
                        {r.run_id} — {r.total_records.toLocaleString()} samples
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            ) : (
              <div className="compare-files-row">
                <label>
                  <span>Baseline file (A)</span>
                  <input
                    type="file"
                    accept=".jtl,.csv,.xml,text/csv,text/plain"
                    onChange={(e) => setCompareFileA(e.target.files?.[0] ?? null)}
                  />
                  {compareFileA && <small className="file-picked">{compareFileA.name}</small>}
                </label>
                <label>
                  <span>Candidate file (B)</span>
                  <input
                    type="file"
                    accept=".jtl,.csv,.xml,text/csv,text/plain"
                    onChange={(e) => setCompareFileB(e.target.files?.[0] ?? null)}
                  />
                  {compareFileB && <small className="file-picked">{compareFileB.name}</small>}
                </label>
              </div>
            )}

            <div className="compare-actions">
              <button
                type="button"
                className="btn-primary btn-primary-large"
                onClick={handleCompareAb}
                disabled={compareLoading}
              >
                {compareLoading
                  ? 'Working…'
                  : saveToLibrary
                    ? 'Generate, save & open HTML'
                    : 'Open comparison report (new tab only)'}
              </button>
            </div>

            {runs.length === 0 && compareMode === 'runs' && (
              <p className="hint-muted">
                No JMeter runs yet. Upload JTL/CSV files on the <strong>JMeter Tests</strong> page, or switch to{' '}
                <strong>Upload two files</strong>.
              </p>
            )}
          </div>

          <div className="content-section saved-reports-section">
            <div className="section-header">
              <h2>Saved comparison reports</h2>
              <span className="section-meta">{savedLoading ? 'Loading…' : `${savedReports.length} saved`}</span>
            </div>
            {!savedLoading && savedReports.length === 0 ? (
              <p className="hint-muted">No saved reports yet. Enable “Save report to library” and generate a comparison.</p>
            ) : (
              <div className="table-container">
                <table className="saved-comparison-table">
                  <thead>
                    <tr>
                      <th>Created</th>
                      <th>Baseline (A)</th>
                      <th>Candidate (B)</th>
                      <th>Source</th>
                      <th>Verdict</th>
                      <th>Signal</th>
                      <th>Size</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {savedReports.map((r) => (
                      <tr key={r.comparison_report_id}>
                        <td className="cell-muted">{formatDate(r.generated_at)}</td>
                        <td>
                          <div className="cell-title">{r.name_a}</div>
                          {r.run_id_a && <div className="cell-sub">{r.run_id_a}</div>}
                        </td>
                        <td>
                          <div className="cell-title">{r.name_b}</div>
                          {r.run_id_b && <div className="cell-sub">{r.run_id_b}</div>}
                        </td>
                        <td>{r.source_type}</td>
                        <td>{r.verdict || '—'}</td>
                        <td>
                          <span className={signalClass(r.traffic_signal)}>
                            {r.traffic_signal || 'green'}
                          </span>
                        </td>
                        <td>{r.file_size ? `${(r.file_size / 1024).toFixed(1)} KB` : '—'}</td>
                        <td>
                          <div className="action-buttons">
                            <button type="button" className="btn-link" onClick={() => handleViewSaved(r.comparison_report_id)}>
                              HTML
                            </button>
                            <button type="button" className="btn-link" onClick={() => handleDownloadSaved(r.comparison_report_id)}>
                              Download
                            </button>
                            <button
                              type="button"
                              className="btn-link"
                              disabled={regeneratingId === r.comparison_report_id}
                              onClick={() => handleRegenerate(r.comparison_report_id)}
                            >
                              {regeneratingId === r.comparison_report_id ? '…' : 'Regenerate'}
                            </button>
                            <button
                              type="button"
                              className="btn-link btn-danger-link"
                              onClick={() => handleDeleteSaved(r.comparison_report_id)}
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PerformanceTestComparePage;
