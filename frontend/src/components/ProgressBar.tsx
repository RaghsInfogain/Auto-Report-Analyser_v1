import React from 'react';
import './ProgressBar.css';

interface ProgressBarProps {
  percent: number;
  label?: string;
  sublabel?: string;
  eta?: string;
  variant?: 'upload' | 'analysis' | 'default';
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  percent,
  label,
  sublabel,
  eta,
  variant = 'default',
}) => {
  const clamped = Math.min(100, Math.max(0, Math.round(percent)));
  return (
    <div className={`progress-bar-wrap progress-bar-${variant}`}>
      {(label || sublabel || eta) && (
        <div className="progress-bar-labels">
          {label && <span className="progress-bar-label">{label}</span>}
          <span className="progress-bar-meta">
            {sublabel && <span className="progress-bar-sublabel">{sublabel}</span>}
            {eta && <span className="progress-bar-eta">Est. {eta}</span>}
          </span>
        </div>
      )}
      <div className="progress-bar-track" role="progressbar" aria-valuenow={clamped} aria-valuemin={0} aria-valuemax={100}>
        <div className="progress-bar-fill" style={{ width: `${clamped}%` }} />
      </div>
      <span className="progress-bar-percent">{clamped}%</span>
    </div>
  );
};

export default ProgressBar;
