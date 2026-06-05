import React, { useState, useEffect } from 'react';
import { getRunTargets, saveRunTargets, RunTargets } from '../services/api';
import './TargetValuesModal.css';

interface TargetValuesModalProps {
  isOpen: boolean;
  runId: string;
  runLabel?: string;
  /** Web Vitals / Lighthouse: hide load-test-only fields (avg RT, error rate, throughput, P95). */
  targetProfile?: 'load_test' | 'web_vitals';
  onClose: () => void;
  onConfirm: (targets: RunTargets) => Promise<void>;
}

const DEFAULT_TARGETS: RunTargets = {
  application_name: '',
  availability_target: 99,
  avg_response_time_target: 2000,
  error_rate_target: 1,
  throughput_target: 100,
  p95_target: 3000,
  sla_compliance_target: 95
};

/** Coerce API / JSON values to finite numbers for target fields. */
function asTargetNumber(value: unknown, fallback: number): number {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const n = parseFloat(value);
    if (Number.isFinite(n)) {
      return n;
    }
  }
  return fallback;
}

const TargetValuesModal: React.FC<TargetValuesModalProps> = ({
  isOpen,
  runId,
  runLabel,
  targetProfile = 'load_test',
  onClose,
  onConfirm
}) => {
  const isWebVitals = targetProfile === 'web_vitals';
  const [targets, setTargets] = useState<RunTargets>({ ...DEFAULT_TARGETS });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && runId) {
      setLoading(true);
      setError(null);
      getRunTargets(runId)
        .then((res) => {
          if (res.targets && typeof res.targets === 'object') {
            const t = res.targets as Record<string, unknown>;
            setTargets({
              application_name:
                t.application_name == null || t.application_name === ''
                  ? ''
                  : String(t.application_name),
              availability_target: asTargetNumber(t.availability_target, DEFAULT_TARGETS.availability_target as number),
              avg_response_time_target: asTargetNumber(
                t.avg_response_time_target,
                DEFAULT_TARGETS.avg_response_time_target as number
              ),
              error_rate_target: asTargetNumber(t.error_rate_target, DEFAULT_TARGETS.error_rate_target as number),
              throughput_target: asTargetNumber(t.throughput_target, DEFAULT_TARGETS.throughput_target as number),
              p95_target: asTargetNumber(t.p95_target, DEFAULT_TARGETS.p95_target as number),
              sla_compliance_target: asTargetNumber(
                t.sla_compliance_target,
                DEFAULT_TARGETS.sla_compliance_target as number
              )
            });
          } else {
            setTargets({ ...DEFAULT_TARGETS });
          }
        })
        .catch((err) => {
          setError(err?.response?.data?.detail || 'Failed to load saved targets');
          setTargets({ ...DEFAULT_TARGETS });
        })
        .finally(() => setLoading(false));
    }
  }, [isOpen, runId]);

  const handleChange = (key: keyof RunTargets, value: string) => {
    if (key === 'application_name') {
      setTargets((prev) => ({ ...prev, application_name: value }));
      return;
    }
    const num = value === '' ? undefined : parseFloat(value);
    setTargets((prev) => ({ ...prev, [key]: num }));
  };

  const handleSubmit = async () => {
    setSaving(true);
    setError(null);
    try {
      await saveRunTargets(runId, targets);
      await onConfirm(targets);
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to save targets');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="target-modal-overlay" onClick={onClose}>
      <div className="target-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="target-modal-header">
          <h2>Target Values for Report</h2>
          <button onClick={onClose} className="target-modal-close" aria-label="Close">×</button>
        </div>
        <p className="target-modal-subtitle">
          Saved with <strong>{runLabel || runId}</strong> and used when generating the report.
        </p>

        {loading ? (
          <div className="target-modal-loading">Loading saved targets...</div>
        ) : (
          <div className="target-modal-form">
            <div className="target-field target-field-full">
              <label htmlFor="app_name">Application name (report title)</label>
              <input
                id="app_name"
                type="text"
                value={targets.application_name ?? ''}
                onChange={(e) => handleChange('application_name', e.target.value)}
                placeholder="e.g. BusinessNext CRM"
                autoComplete="off"
                title={
                  isWebVitals
                    ? 'Shown in the report header.'
                    : 'Shown in the report header. Blank = inferred from JMeter data.'
                }
              />
              <span className="target-hint">
                {isWebVitals
                  ? 'Shown in the report header.'
                  : 'Report header; leave blank to infer from JMeter.'}
              </span>
            </div>

            <div className="target-field">
              <label htmlFor="availability">Availability (%)</label>
              <input
                id="availability"
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={targets.availability_target ?? ''}
                onChange={(e) => handleChange('availability_target', e.target.value)}
                placeholder="99"
                title="e.g. 99.9 for 99.9%"
              />
            </div>

            {!isWebVitals && (
            <div className="target-field">
              <label htmlFor="avg_response">Avg response (ms)</label>
              <input
                id="avg_response"
                type="number"
                min="0"
                step="100"
                value={targets.avg_response_time_target ?? ''}
                onChange={(e) => handleChange('avg_response_time_target', e.target.value)}
                placeholder="2000"
                title="e.g. 2000 for 2 seconds"
              />
            </div>
            )}

            {!isWebVitals && (
            <div className="target-field">
              <label htmlFor="error_rate">Error rate (%)</label>
              <input
                id="error_rate"
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={targets.error_rate_target ?? ''}
                onChange={(e) => handleChange('error_rate_target', e.target.value)}
                placeholder="1"
                title="e.g. 1 for 1%"
              />
            </div>
            )}

            {!isWebVitals && (
            <div className="target-field">
              <label htmlFor="throughput">Throughput (req/s)</label>
              <input
                id="throughput"
                type="number"
                min="0"
                step="10"
                value={targets.throughput_target ?? ''}
                onChange={(e) => handleChange('throughput_target', e.target.value)}
                placeholder="100"
                title="Requests per second"
              />
            </div>
            )}

            {!isWebVitals && (
            <div className="target-field">
              <label htmlFor="p95">95th percentile (ms)</label>
              <input
                id="p95"
                type="number"
                min="0"
                step="100"
                value={targets.p95_target ?? ''}
                onChange={(e) => handleChange('p95_target', e.target.value)}
                placeholder="3000"
                title="e.g. 3000 for 3 seconds"
              />
            </div>
            )}

            <div className="target-field">
              <label htmlFor="sla">SLA compliance (%)</label>
              <input
                id="sla"
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={targets.sla_compliance_target ?? ''}
                onChange={(e) => handleChange('sla_compliance_target', e.target.value)}
                placeholder="95"
                title="% of requests meeting SLA"
              />
            </div>
          </div>
        )}

        {error && <div className="target-modal-error">{error}</div>}

        <div className="target-modal-actions">
          <button type="button" onClick={onClose} className="target-btn-cancel">
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading || saving}
            className="target-btn-confirm"
          >
            {saving ? 'Saving & Generating...' : 'Save & Generate Report'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TargetValuesModal;
