"""
Shared CSS for JMeter, comparative (AB), and Web Vitals / Lighthouse HTML reports.

Tokens and component rules align with jmeter_perf_report_businessnext_crmuat.html.
"""

# Full :root — reference file used these names without defining them; legacy aliases keep older rules working.
CSS_ROOT = """
        :root {
            --font-sans: 'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
            --color-text-primary: #1e293b;
            --color-text-secondary: #64748b;
            --color-border-tertiary: #e5e7eb;
            --color-border-secondary: #d1d5db;
            --color-border-info: #93c5fd;
            --color-background-primary: #ffffff;
            --color-background-secondary: #f4f4f2;
            --color-background-info: #e0f2fe;
            --color-text-info: #0c447c;
            --border-radius-md: 6px;
            --border-radius-lg: 10px;

            --primary-color: #2563eb;
            --success-color: #059669;
            --warning-color: #d97706;
            --danger-color: #dc2626;
            --secondary-color: #64748b;
            --background-light: #ffffff;
            --card-background: var(--color-background-primary);
            --text-primary: var(--color-text-primary);
            --text-secondary: var(--color-text-secondary);
            --border-color: var(--color-border-tertiary);
        }
"""

# Snippet from jmeter_perf_report_businessnext_crmuat.html (component vocabulary).
CSS_BUSINESSNEXT_COMPONENTS = """
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: var(--font-sans);
            color: var(--color-text-primary);
            background-color: var(--background-light);
            line-height: 1.6;
        }
        .section { margin-bottom: 2rem; }
        .section-title {
            font-size: 11px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: .08em;
            color: var(--color-text-secondary);
            margin-bottom: .75rem;
            padding-bottom: .4rem;
            border-bottom: .5px solid var(--color-border-tertiary);
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 10px;
            margin-bottom: 1.5rem;
        }
        .metric {
            background: var(--color-background-secondary);
            border-radius: var(--border-radius-md);
            padding: .9rem 1rem;
        }
        .metric-label {
            font-size: 11px;
            color: var(--color-text-secondary);
            margin-bottom: .3rem;
        }
        .metric-value {
            font-size: 22px;
            font-weight: 500;
        }
        .metric-sub {
            font-size: 11px;
            color: var(--color-text-secondary);
            margin-top: .2rem;
        }
        .verdict {
            border-radius: var(--border-radius-lg);
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.5rem;
            border: .5px solid;
        }
        .verdict-nogo {
            background: #FCEBEB;
            border-color: #F09595;
            color: #501313;
        }
        .verdict-title {
            font-size: 18px;
            font-weight: 500;
            margin-bottom: .4rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .verdict-body { font-size: 13px; line-height: 1.7; }
        .badge {
            display: inline-block;
            font-size: 11px;
            font-weight: 500;
            padding: 2px 8px;
            border-radius: 4px;
        }
        .badge-fail { background: #F7C1C1; color: #791F1F; }
        .badge-warn { background: #FAC775; color: #633806; }
        .badge-pass { background: #C0DD97; color: #3B6D11; }
        .badge-info { background: #B5D4F4; color: #0C447C; }
        .issue-card {
            background: var(--color-background-primary);
            border: .5px solid var(--color-border-tertiary);
            border-radius: var(--border-radius-md);
            padding: .9rem 1rem;
            margin-bottom: .6rem;
        }
        .issue-title {
            font-size: 13px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: .3rem;
        }
        .issue-body {
            font-size: 12px;
            color: var(--color-text-secondary);
            line-height: 1.6;
        }
        .res-row {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            padding: .6rem 0;
            border-bottom: .5px solid var(--color-border-tertiary);
            font-size: 12px;
        }
        .res-row:last-child { border-bottom: none; }
        .res-num {
            background: var(--color-background-info);
            color: var(--color-text-info);
            font-weight: 500;
            font-size: 11px;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            margin-top: 1px;
        }
        .res-content { flex: 1; }
        .res-title { font-weight: 500; font-size: 13px; margin-bottom: 2px; }
        .tx-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
        }
        .tx-table th {
            text-align: left;
            padding: 5px 8px;
            color: var(--color-text-secondary);
            font-weight: 400;
            border-bottom: .5px solid var(--color-border-tertiary);
        }
        .tx-table td {
            padding: 5px 8px;
            border-bottom: .5px solid var(--color-border-tertiary);
        }
        .tx-table tr:last-child td { border-bottom: none; }
        .tab-row {
            display: flex;
            gap: 8px;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }
        .tab-btn {
            font-size: 12px;
            padding: 4px 12px;
            border-radius: 4px;
            cursor: pointer;
            background: var(--color-background-secondary);
            border: .5px solid var(--color-border-secondary);
            color: var(--color-text-primary);
        }
        .tab-btn.active {
            background: var(--color-background-info);
            color: var(--color-text-info);
            border-color: var(--color-border-info);
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .health-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-bottom: 1rem;
        }
        .health-card {
            background: var(--color-background-primary);
            border: .5px solid var(--color-border-tertiary);
            border-radius: var(--border-radius-md);
            padding: 1rem;
        }
        .health-label {
            font-size: 11px;
            color: var(--color-text-secondary);
            margin-bottom: 6px;
        }
        .health-bar-bg {
            background: var(--color-background-secondary);
            border-radius: 4px;
            height: 8px;
            overflow: hidden;
        }
        .health-bar { height: 8px; border-radius: 4px; }
        .rec-item {
            display: flex;
            gap: 10px;
            padding: .5rem 0;
            border-bottom: .5px solid var(--color-border-tertiary);
            font-size: 12px;
            align-items: flex-start;
        }
        .rec-item:last-child { border-bottom: none; }
        .priority-high {
            color: #A32D2D;
            font-size: 10px;
            font-weight: 500;
            background: #FCEBEB;
            padding: 1px 6px;
            border-radius: 3px;
            white-space: nowrap;
        }
        .priority-med {
            color: #854F0B;
            font-size: 10px;
            font-weight: 500;
            background: #FAEEDA;
            padding: 1px 6px;
            border-radius: 3px;
            white-space: nowrap;
        }
        .priority-low {
            color: #3B6D11;
            font-size: 10px;
            font-weight: 500;
            background: #EAF3DE;
            padding: 1px 6px;
            border-radius: 3px;
            white-space: nowrap;
        }
        h2 { font-size: 16px; font-weight: 500; margin-bottom: .4rem; }
"""

# JMeter generator: card-style sections, legacy class bridges, charts, print.
CSS_JMETER_LAYOUT = """
        .header {
            background: linear-gradient(135deg, var(--primary-color), #3b82f6);
            color: white;
            padding: 2rem 0;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .header p { font-size: 1.2rem; opacity: 0.9; }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 1rem;
        }
        .section {
            background: var(--color-background-primary);
            margin: 2rem 0;
            padding: 2rem;
            border-radius: var(--border-radius-lg);
            border: .5px solid var(--color-border-tertiary);
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
        }
        .section h2 {
            color: var(--color-text-primary);
            font-size: 1.25rem;
            margin-bottom: 1.5rem;
            padding-bottom: 0.5rem;
            border-bottom: .5px solid var(--color-border-tertiary);
        }
        .section h3 {
            color: var(--color-text-primary);
            font-size: 1rem;
            font-weight: 600;
            margin: 1.5rem 0 1rem 0;
        }
        .status-badge {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9rem;
            margin: 0.25rem;
        }
        .badge-success { background: var(--success-color); color: white; }
        .badge-warning { background: var(--warning-color); color: white; }
        .badge-danger { background: var(--danger-color); color: white; }
        .badge-info { background: var(--primary-color); color: white; }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 10px;
            margin: 1.5rem 0;
        }
        .metric-card {
            background: var(--color-background-secondary);
            border: .5px solid var(--color-border-tertiary);
            border-radius: var(--border-radius-md);
            padding: .9rem 1rem;
            text-align: left;
            transition: transform 0.2s, box-shadow 0.2s;
            min-height: 120px;
            display: flex;
            flex-direction: column;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }
        .metric-card.success { border-color: #C0DD97; }
        .metric-card.warning { border-color: #FAC775; }
        .metric-card.danger { border-color: #F09595; }
        .metric-card .metric-value {
            font-size: 22px;
            font-weight: 500;
            margin-bottom: 0.35rem;
        }
        .metric-card .metric-value.success { color: var(--success-color); }
        .metric-card .metric-value.warning { color: var(--warning-color); }
        .metric-card .metric-value.danger { color: var(--danger-color); }
        .metric-card .metric-label {
            font-size: 11px;
            color: var(--color-text-secondary);
            text-transform: none;
            font-weight: 500;
        }
        .chart-container {
            position: relative;
            height: 400px;
            margin: 2rem 0;
        }
        .two-column {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            align-items: start;
        }
        .issue-item {
            background: #FCEBEB;
            border-left: 4px solid var(--danger-color);
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 0 var(--border-radius-md) var(--border-radius-md) 0;
        }
        .issue-item h4 { color: var(--danger-color); margin-bottom: 0.5rem; }
        .endpoint-table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 11px;
            background: var(--color-background-primary);
            border: .5px solid var(--color-border-tertiary);
        }
        .endpoint-table th,
        .endpoint-table td {
            padding: 5px 8px;
            text-align: left;
            border-bottom: .5px solid var(--color-border-tertiary);
            vertical-align: middle;
        }
        .endpoint-table thead {
            background: var(--color-background-secondary);
        }
        .endpoint-table th {
            font-weight: 400;
            color: var(--color-text-secondary);
            font-size: 11px;
        }
        .endpoint-table td { color: var(--color-text-primary); }
        .endpoint-table tbody tr { transition: background 0.2s; }
        .endpoint-table tbody tr:hover { background: var(--color-background-secondary); }
        .endpoint-table tbody tr:last-child td { border-bottom: none; }
        .action-timeline { position: relative; padding: 1rem 0; }
        .timeline-item {
            position: relative;
            padding: 1rem 0 1rem 3rem;
            border-left: 2px solid var(--border-color);
        }
        .timeline-item::before {
            content: '';
            position: absolute;
            left: -6px;
            top: 1.5rem;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--primary-color);
        }
        .timeline-item.danger::before { background: var(--danger-color); }
        .timeline-item.warning::before { background: var(--warning-color); }
        .timeline-item.success::before { background: var(--success-color); }
        .alert {
            padding: 1rem;
            border-radius: var(--border-radius-md);
            margin: 1rem 0;
            border: 1px solid;
        }
        .alert-danger {
            background: #FCEBEB;
            border-color: #F09595;
            color: #501313;
        }
        .alert-warning {
            background: #FAEEDA;
            border-color: var(--warning-color);
            color: #633806;
        }
        .alert-success {
            background: #EAF3DE;
            border-color: var(--success-color);
            color: #166534;
        }
        .executive-summary {
            background: linear-gradient(135deg, #334155 0%, #475569 55%, #1e293b 100%);
            color: white;
            padding: 2rem;
            border-radius: var(--border-radius-lg);
            margin: 2rem 0;
            border: .5px solid #64748b;
        }
        .executive-summary .metric-label,
        .executive-summary .section-title { color: rgba(255,255,255,0.85); }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        .summary-item {
            text-align: center;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: var(--border-radius-md);
        }
        .summary-value {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background: var(--color-border-tertiary);
            border-radius: 10px;
            overflow: hidden;
            margin: 0.5rem 0;
        }
        .progress-fill { height: 100%; transition: width 0.3s ease; }
        .progress-success { background: var(--success-color); }
        .progress-warning { background: var(--warning-color); }
        .progress-danger { background: var(--danger-color); }
        @media (max-width: 768px) {
            .header h1 { font-size: 2rem; }
            .two-column { grid-template-columns: 1fr; }
            .metrics-grid { grid-template-columns: repeat(2, 1fr); }
            .health-grid { grid-template-columns: 1fr; }
        }
        @media (max-width: 600px) {
            .metrics-grid { grid-template-columns: 1fr; }
        }
        @media print {
            .no-print { display: none !important; }
            .pdf-button { display: none !important; }
            body { margin: 0; padding: 0; }
            .container { max-width: 100%; padding: 1rem; }
            .section {
                page-break-inside: avoid;
                max-width: 100%;
                overflow: hidden;
            }
            .card, .alert, .summary-item { box-shadow: none; }
            .endpoint-table { font-size: 10px; }
            .endpoint-table th, .endpoint-table td { padding: 4px 6px; }
        }
        .pdf-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(102, 126, 234, 0.5) !important;
        }
        .pdf-button:active { transform: translateY(0); }
"""


def build_jmeter_report_css() -> str:
    return (
        "<style>"
        + CSS_ROOT
        + CSS_BUSINESSNEXT_COMPONENTS
        + CSS_JMETER_LAYOUT
        + "</style>"
    )


# Lighthouse / Web Vitals: same theme + report-specific layout (no second :root).
CSS_LIGHTHOUSE_LAYOUT = """
        body { padding: 1rem 0; }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 1rem;
        }
        .header {
            background: linear-gradient(135deg, var(--primary-color), #3b82f6);
            color: white;
            padding: 2rem;
            text-align: center;
            border-radius: var(--border-radius-lg);
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .section {
            background: var(--color-background-primary);
            margin: 1.5rem 0;
            padding: 1.5rem;
            border-radius: var(--border-radius-md);
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
            border: .5px solid var(--color-border-tertiary);
        }
        .section h2 {
            color: var(--color-text-primary);
            font-size: 1.125rem;
            font-weight: 600;
            margin: 0 0 1.5rem 0;
            padding-bottom: 1rem;
            border-bottom: .5px solid var(--color-border-tertiary);
        }
        .section h3 {
            color: var(--color-text-primary);
            font-size: 1rem;
            font-weight: 600;
            margin: 1.5rem 0 1rem 0;
        }
        .executive-summary {
            background: var(--color-background-primary);
            color: var(--color-text-primary);
            padding: 1.5rem;
            border-radius: var(--border-radius-md);
            margin: 1.5rem 0;
            border: .5px solid var(--color-border-tertiary);
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1.5rem 0;
        }
        .summary-item {
            text-align: center;
            padding: 1rem;
            background: var(--color-background-secondary);
            border-radius: var(--border-radius-md);
            border: .5px solid var(--color-border-tertiary);
        }
        .summary-value {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .summary-label { font-size: 0.9rem; color: var(--color-text-secondary); }
        .grade-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-weight: 500;
            font-size: 0.75rem;
            margin: 0.5rem;
        }
        .grade-a { background: #EAF3DE; color: #3B6D11; }
        .grade-b { background: #e0f2fe; color: #0c447c; }
        .grade-c { background: #FAEEDA; color: #633806; }
        .grade-d { background: #FCEBEB; color: #791F1F; }
        .grade-e { background: #FCEBEB; color: #791F1F; }
        .grade-f { background: #FCEBEB; color: #791F1F; }
        .scorecard-card {
            background: var(--color-background-primary);
            border: .5px solid var(--color-border-tertiary);
            border-radius: var(--border-radius-md);
            padding: 1.5rem;
            text-align: center;
            transition: box-shadow 0.2s;
            min-height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        .scorecard-card:hover {
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }
        .scorecard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin: 1.5rem 0;
        }
        .card-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--color-text-primary);
            margin-bottom: 0.5rem;
            word-wrap: break-word;
            overflow-wrap: break-word;
            line-height: 1.2;
            max-width: 100%;
        }
        .card-value-large {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--color-text-primary);
            margin-bottom: 0.5rem;
            word-wrap: break-word;
            overflow-wrap: break-word;
            line-height: 1.2;
            max-width: 100%;
        }
        @media (max-width: 768px) {
            .card-value { font-size: 2rem; }
            .card-value-large { font-size: 1.4rem; }
            .scorecard-card { min-height: 120px; }
            .category-card { min-height: 180px; }
        }
        .scorecard-card > * { max-width: 100%; }
        .category-card > * { max-width: 100%; }
        .card-title {
            margin: 0.5rem 0;
            color: var(--color-text-primary);
            font-size: 0.875rem;
            font-weight: 600;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        .card-description {
            margin: 0;
            color: var(--color-text-secondary);
            font-size: 0.875rem;
            word-wrap: break-word;
            overflow-wrap: break-word;
            line-height: 1.4;
        }
        .category-card {
            background: var(--color-background-secondary);
            border: .5px solid var(--color-border-tertiary);
            border-radius: var(--border-radius-md);
            padding: 1.5rem;
            text-align: center;
            word-wrap: break-word;
            overflow-wrap: break-word;
            overflow: hidden;
            min-height: 150px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .category-card p {
            word-wrap: break-word;
            overflow-wrap: break-word;
            line-height: 1.4;
            max-width: 100%;
        }
        .grade-card {
            background: var(--color-background-primary);
            border: .5px solid var(--color-border-tertiary);
            border-radius: var(--border-radius-md);
            padding: 1rem;
            margin: 0.5rem 0;
        }
        .risk-card {
            padding: 1.5rem;
            border-radius: var(--border-radius-md);
            margin: 1.5rem 0;
            background: var(--color-background-primary);
            border: .5px solid var(--color-border-tertiary);
        }
        table {
            width: 100%;
            max-width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 11px;
            background: var(--color-background-primary);
            border: .5px solid var(--color-border-tertiary);
            table-layout: auto;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        table th,
        table td {
            padding: 5px 8px;
            text-align: left;
            border-bottom: .5px solid var(--color-border-tertiary);
            vertical-align: middle;
            word-wrap: break-word;
            overflow-wrap: break-word;
            max-width: 200px;
        }
        table thead {
            background: var(--color-background-secondary);
        }
        table th {
            font-weight: 400;
            color: var(--color-text-secondary);
            font-size: 11px;
        }
        table td {
            color: var(--color-text-primary);
            padding: 5px 8px;
        }
        table tbody tr { transition: background 0.2s; background: var(--color-background-primary); }
        table tbody tr:hover { background: var(--color-background-secondary); }
        table tbody tr:last-child td { border-bottom: none; }
        .status-good {
            color: #065f46;
            font-weight: 600;
            background: #d1fae5;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            display: inline-block;
        }
        .status-warning {
            color: #92400e;
            font-weight: 600;
            background: #fef3c7;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            display: inline-block;
        }
        .status-poor {
            color: #991b1b;
            font-weight: 600;
            background: #fee2e2;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            display: inline-block;
        }
        .status-critical {
            color: #991b1b;
            font-weight: 700;
            background: #fecaca;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            display: inline-block;
        }
        .severity-low { background: #d1fae5; color: #065f46; padding: 0.25rem 0.5rem; border-radius: 4px; }
        .severity-medium { background: #fef3c7; color: #92400e; padding: 0.25rem 0.5rem; border-radius: 4px; }
        .severity-high { background: #fee2e2; color: #991b1b; padding: 0.25rem 0.5rem; border-radius: 4px; }
        .severity-critical { background: #fecaca; color: #7f1d1d; padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: 700; }
        .alert {
            padding: 1rem;
            border-radius: var(--border-radius-md);
            margin: 1rem 0;
            border-left: 4px solid;
        }
        .alert-danger {
            background: #FCEBEB;
            border-color: #E24B4A;
            color: #501313;
        }
        .alert-warning {
            background: #FAEEDA;
            border-color: var(--warning-color);
            color: #633806;
        }
        .phase-section {
            margin: 1.5rem 0;
            padding: 1rem;
            background: var(--color-background-secondary);
            border-radius: var(--border-radius-md);
            border: .5px solid var(--color-border-tertiary);
        }
        .footer {
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: .5px solid var(--color-border-tertiary);
            text-align: center;
            color: var(--color-text-secondary);
            font-size: 0.875rem;
        }
        @media (max-width: 768px) {
            .header h1 { font-size: 1.25rem; }
            .summary-grid { grid-template-columns: 1fr; }
            .scorecard-grid { grid-template-columns: 1fr; }
            table { font-size: 0.75rem; }
            .card-value { font-size: 1.25rem; }
            .card-value-large { font-size: 1rem; }
            .scorecard-card { min-height: 100px; }
            .category-card { min-height: 120px; }
        }
"""


def build_lighthouse_report_css() -> str:
    return (
        "<style>"
        + CSS_ROOT
        + CSS_BUSINESSNEXT_COMPONENTS
        + CSS_LIGHTHOUSE_LAYOUT
        + "</style>"
    )
