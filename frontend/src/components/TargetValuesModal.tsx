import React, { useState, useEffect } from 'react';
import { getRunTargets, saveRunTargets, RunTargets } from '../services/api';
import './TargetValuesModal.css';

interface TargetValuesModalProps {
  isOpen: boolean;
  runId: string;
  runLabel?: string;
  onClose: () => void;
  onConfirm: (targets: RunTargets) => Promise<void>;
}

const DEFAULT_TARGETS: RunTargets = {
  availability_target: 99,
  avg_response_time_target: 2000,
  error_rate_target: 1,
  throughput_target: 100,
  p95_target: 3000,
  sla_compliance_target: 95
};

const TargetValuesModal: React.FC<TargetValuesModalProps> = ({
  isOpen,
  runId,
  runLabel,
  onClose,
  onConfirm
}) => {
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
            const t = res.targets as Record<string, number | undefined>;
            setTargets({
              availability_target: t.availability_target ?? DEFAULT_TARGETS.availability_target,
              avg_response_time_target: t.avg_response_time_target ?? DEFAULT_TARGETS.avg_response_time_target,
              error_rate_target: t.error_rate_target ?? DEFAULT_TARGETS.error_rate_target,
              throughput_target: t.throughput_target ?? DEFAULT_TARGETS.throughput_target,
              p95_target: t.p95_target ?? DEFAULT_TARGETS.p95_target,
              sla_compliance_target: t.sla_compliance_target ?? DEFAULT_TARGETS.sla_compliance_target
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
          Enter your SLA/target values. These will be saved with {runLabel || runId} and used for report generation.
        </p>

        {loading ? (
          <div className="target-modal-loading">Loading saved targets...</div>
        ) : (
          <div className="target-modal-form">
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
              />
              <span className="target-hint">e.g. 99.9 for 99.9%</span>
            </div>

            <div className="target-field">
              <label htmlFor="avg_response">Average Response Time (ms)</label>
              <input
                id="avg_response"
                type="number"
                min="0"
                step="100"
                value={targets.avg_response_time_target ?? ''}
                onChange={(e) => handleChange('avg_response_time_target', e.target.value)}
                placeholder="2000"
              />
              <span className="target-hint">e.g. 2000 for 2 seconds</span>
            </div>

            <div className="target-field">
              <label htmlFor="error_rate">Error Rate (%)</label>
              <input
                id="error_rate"
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={targets.error_rate_target ?? ''}
                onChange={(e) => handleChange('error_rate_target', e.target.value)}
                placeholder="1"
              />
              <span className="target-hint">e.g. 1 for 1%</span>
            </div>

            <div className="target-field">
              <label htmlFor="throughput">Throughput (req/sec)</label>
              <input
                id="throughput"
                type="number"
                min="0"
                step="10"
                value={targets.throughput_target ?? ''}
                onChange={(e) => handleChange('throughput_target', e.target.value)}
                placeholder="100"
              />
              <span className="target-hint">requests per second</span>
            </div>

            <div className="target-field">
              <label htmlFor="p95">95th Percentile (ms)</label>
              <input
                id="p95"
                type="number"
                min="0"
                step="100"
                value={targets.p95_target ?? ''}
                onChange={(e) => handleChange('p95_target', e.target.value)}
                placeholder="3000"
              />
              <span className="target-hint">e.g. 3000 for 3 seconds</span>
            </div>

            <div className="target-field">
              <label htmlFor="sla">SLA Compliance (%)</label>
              <input
                id="sla"
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={targets.sla_compliance_target ?? ''}
                onChange={(e) => handleChange('sla_compliance_target', e.target.value)}
                placeholder="95"
              />
              <span className="target-hint">% of requests meeting SLA</span>
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
