import React from 'react';

export interface PageShellProps {
  iconClass?: string;
  iconTone?: 'bl' | 'gn' | 'am' | 'pu';
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  legend?: React.ReactNode;
}

const PageShell: React.FC<PageShellProps> = ({
  iconClass = 'ti ti-chart-infographic',
  iconTone = 'bl',
  title,
  subtitle,
  actions,
  children,
  legend,
}) => (
  <div className="ent-page">
    <header className="ent-ph">
      <div className={`ent-ph-ic ${iconTone}`}>
        <i className={iconClass} aria-hidden />
      </div>
      <div className="ent-ph-body">
        <h1 className="ent-ph-ttl">{title}</h1>
        {subtitle && <p className="ent-ph-mt">{subtitle}</p>}
      </div>
      {actions && <div className="ent-ph-act">{actions}</div>}
    </header>
    {legend && (
      <div
        className="ent-legend-bar"
        style={{
          padding: '10px 26px',
          background: 'var(--sur)',
          borderBottom: '1px solid var(--brd)',
          display: 'flex',
          gap: 18,
          flexWrap: 'wrap',
          fontSize: 11,
          color: 'var(--ink3)',
          alignItems: 'center',
        }}
      >
        {legend}
      </div>
    )}
    <div className="ent-body">{children}</div>
  </div>
);

export default PageShell;
