import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  sla_compliance_target: 95,
};

type TargetFieldKey = keyof RunTargets;

const TARGET_FIELDS: {
  key: TargetFieldKey;
  label: string;
  placeholder: string;
  title: string;
  min?: number;
  max?: number;
  step?: number | string;
}[] = [
  {
    key: 'availability_target',
    label: 'Availability (%)',
    placeholder: '99',
    title: 'Target availability, e.g. 99.9',
    min: 0,
    max: 100,
    step: 0.1,
  },
  {
    key: 'avg_response_time_target',
    label: 'Avg RT (ms)',
    placeholder: '2000',
    title: 'Average response time in ms, e.g. 2000 = 2s',
    min: 0,
    step: 100,
  },
  {
    key: 'error_rate_target',
    label: 'Error rate (%)',
    placeholder: '1',
    title: 'Maximum error rate, e.g. 1%',
    min: 0,
    max: 100,
    step: 0.1,
  },
  {
    key: 'throughput_target',
    label: 'Throughput (/s)',
    placeholder: '100',
    title: 'Requests per second',
    min: 0,
    step: 10,
  },
  {
    key: 'p95_target',
    label: 'P95 (ms)',
    placeholder: '3000',
    title: '95th percentile in ms, e.g. 3000 = 3s',
    min: 0,
    step: 100,
  },
  {
    key: 'sla_compliance_target',
    label: 'SLA compliance (%)',
    placeholder: '95',
    title: 'Percent of requests meeting SLA',
    min: 0,
    max: 100,
    step: 0.1,
  },
];

const TargetValuesModal: React.FC<TargetValuesModalProps> = ({
  isOpen,
  runId,
  runLabel,
  onClose,
  onConfirm,
}) => {
  const [targets, setTargets] = useState<RunTargets>({ ...DEFAULT_TARGETS });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragState = useRef({ active: false, startX: 0, startY: 0, origX: 0, origY: 0 });

  useEffect(() => {
    if (isOpen) {
      setDragOffset({ x: 0, y: 0 });
    }
  }, [isOpen, runId]);

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
              avg_response_time_target:
                t.avg_response_time_target ?? DEFAULT_TARGETS.avg_response_time_target,
              error_rate_target: t.error_rate_target ?? DEFAULT_TARGETS.error_rate_target,
              throughput_target: t.throughput_target ?? DEFAULT_TARGETS.throughput_target,
              p95_target: t.p95_target ?? DEFAULT_TARGETS.p95_target,
              sla_compliance_target:
                t.sla_compliance_target ?? DEFAULT_TARGETS.sla_compliance_target,
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

  const handleChange = (key: TargetFieldKey, value: string) => {
    const num = value === '' ? undefined : parseFloat(value);
    setTargets((prev) => ({ ...prev, [key]: num }));
  };

  const handleHeaderPointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if ((e.target as HTMLElement).closest('.target-modal-close')) return;
      dragState.current = {
        active: true,
        startX: e.clientX,
        startY: e.clientY,
        origX: dragOffset.x,
        origY: dragOffset.y,
      };
      setIsDragging(true);
      e.currentTarget.setPointerCapture(e.pointerId);
      e.preventDefault();
    },
    [dragOffset.x, dragOffset.y],
  );

  const handleHeaderPointerMove = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragState.current.active) return;
    setDragOffset({
      x: dragState.current.origX + (e.clientX - dragState.current.startX),
      y: dragState.current.origY + (e.clientY - dragState.current.startY),
    });
  }, []);

  const endDrag = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragState.current.active) return;
    dragState.current.active = false;
    setIsDragging(false);
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
  }, []);

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
      <div
        className={`target-modal-content${isDragging ? ' is-dragging' : ''}`}
        style={{
          transform: `translate(calc(-50% + ${dragOffset.x}px), calc(-50% + ${dragOffset.y}px))`,
        }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="target-modal-title"
      >
        <div
          className="target-modal-header"
          onPointerDown={handleHeaderPointerDown}
          onPointerMove={handleHeaderPointerMove}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
        >
          <h2 id="target-modal-title">Target values</h2>
          <button type="button" onClick={onClose} className="target-modal-close" aria-label="Close">
            ×
          </button>
        </div>
        <p className="target-modal-subtitle" title={`SLA targets for ${runLabel || runId}`}>
          SLA targets · {runLabel || runId}
        </p>

        <div className="target-modal-body">
          {loading ? (
            <div className="target-modal-loading">Loading…</div>
          ) : (
            <div className="target-modal-form">
              {TARGET_FIELDS.map((field) => (
                <div key={field.key} className="target-field">
                  <label htmlFor={`target-${field.key}`}>{field.label}</label>
                  <input
                    id={`target-${field.key}`}
                    type="number"
                    min={field.min}
                    max={field.max}
                    step={field.step}
                    value={targets[field.key] ?? ''}
                    onChange={(e) => handleChange(field.key, e.target.value)}
                    placeholder={field.placeholder}
                    title={field.title}
                  />
                </div>
              ))}
            </div>
          )}
        </div>

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
            {saving ? 'Saving…' : 'Save & generate'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TargetValuesModal;
