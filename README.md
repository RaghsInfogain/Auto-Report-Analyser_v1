# Auto Report Analyzer v3.0.0

A comprehensive performance analysis application for analyzing Web Vitals, JMeter test results, and UI Performance metrics with **AI-powered Release Intelligence**.

## 🚀 Key Features

### Performance Testing & Analysis
- **Multi-format Support**: Upload JSON, CSV, and JTL files
- **Three Analysis Categories**:
  - Web Vitals (LCP, FID, CLS, FCP, TTFB, INP)
  - JMeter Test Results (latency, throughput, error rates)
  - UI Performance (DNS lookup, connection time, page load time)
- **Comprehensive Reports**: Generate detailed performance reports with recommendations
- **Statistical Analysis**: Mean, median, P95, P99 metrics

### 🎯 Release Intelligence (NEW in v3.0.0)
- **Baseline Management**: Create and track performance baselines
- **Automated Regression Detection**: Compare current vs baseline performance
- **Release Readiness Scoring**: AI-powered release decision recommendations
- **Correlation Analysis**: Detect backend/frontend performance issues
- **Natural Language Reports**: Auto-generated executive summaries
- **Visual UI**: Three dedicated pages for baselines, comparisons, and release decisions

### Other Features
- **AI Chatbot**: Intelligent assistant for performance analysis
- **Modern UI**: React-based frontend with TypeScript
- **Authentication**: Secure login system with role-based access

## 📚 Documentation

All comprehensive documentation is now organized in the **`docs/`** folder:

- **[docs/INDEX.md](docs/INDEX.md)** - Complete documentation index
- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - Quick start guide
- **[docs/UI_COMPARISON_FEATURES.md](docs/UI_COMPARISON_FEATURES.md)** - Guide to comparison UI
- **[docs/QUICK_START_COMPARISON.md](docs/QUICK_START_COMPARISON.md)** - Comparison engine quick start
- **[docs/EXECUTIVE_SUMMARY_COMPARISON.md](docs/EXECUTIVE_SUMMARY_COMPARISON.md)** - Business overview

[**→ Browse all documentation**](docs/INDEX.md)

## Project Structure

```
AutoReportAnalyzer/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── models/         # Data models
│   │   ├── parsers/        # File parsers (JSON, CSV, JTL)
│   │   ├── analyzers/      # Analysis logic
│   │   ├── comparison/     # NEW: Comparison & release intelligence engine
│   │   ├── report_generator/ # Report generation
│   │   ├── database/       # Database models and service
│   │   └── api/            # API routes
│   ├── requirements.txt
│   └── uploads/            # Uploaded files storage
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components (Dashboard, Baselines, Compare, etc.)
│   │   └── services/       # API services
│   └── package.json
├── docs/                   # 📚 Comprehensive documentation (23 files)
└── sample_data/            # Sample test data files
```

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the server:
```bash
uvicorn app.main:app --reload --port 8010
```

The backend API will be available at `http://localhost:8010`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The frontend will be available at `http://localhost:3020`

### Running on Windows

Use the provided `.bat` scripts (equivalent to the `.sh` scripts on macOS/Linux):

| Script | Description |
|--------|-------------|
| `run_server.bat` | Start both backend and frontend (opens two windows). Backend: http://localhost:8010, Frontend: http://localhost:3020 |
| `start_backend.bat` | Backend only (FastAPI on port 8010) |
| `start_frontend.bat` | Frontend only (React on port 3020) |
| `run_backend.bat` | Backend only, with venv setup and dependency check |
| `run_frontend.bat` | Frontend only, with npm install if needed |
| `restart_standard_ports.bat` | Stop processes on ports 6000, 7001, 8010, 3000, 3020 and restart backend and frontend |
| `migrate_to_sequential_runs.bat` | Run the Run ID migration script (requires backend venv) |

**Prerequisites on Windows:** Python 3 (or `py -3`), Node.js/npm. Double-click a `.bat` file or run it from Command Prompt.

## Usage

1. **Upload Files**: Select multiple files and assign categories (Web Vitals, JMeter, UI Performance)
2. **Analyze**: Select uploaded files and click "Analyze Selected Files"
3. **Generate Report**: Click "Generate Comprehensive Report" to create a detailed performance report

## API Endpoints

### Core APIs
- `POST /api/upload` - Upload files with categories
- `GET /api/files` - List all uploaded files
- `GET /api/runs` - List all test runs
- `POST /api/analyze` - Analyze selected files
- `POST /api/report/generate` - Generate comprehensive report
- `GET /api/health` - Health check

### Comparison & Release Intelligence APIs (NEW)
- `POST /api/comparison/baseline/set` - Create a new baseline
- `GET /api/comparison/baseline/list` - List all baselines
- `POST /api/comparison/compare` - Run performance comparison
- `GET /api/comparison/compare/result/{id}` - Get comparison results
- `GET /api/comparison/release/verdict/{id}` - Get release verdict
- `GET /api/comparison/release/regressions/{id}` - Get regression details

[**→ Interactive API docs**](http://localhost:8010/docs) (when server is running)

## File Format Examples

### Web Vitals (JSON)
```json
{
  "lcp": 2500,
  "fid": 100,
  "cls": 0.1,
  "fcp": 1800,
  "ttfb": 600,
  "url": "https://example.com"
}
```

### JMeter (CSV)
```csv
timeStamp,elapsed,label,responseCode,success,Latency
1234567890,150,Homepage,200,true,140
```

### UI Performance (JSON)
```json
{
  "dns_lookup_time": 50,
  "connection_time": 100,
  "page_load_time": 2000,
  "full_page_load_time": 3000
}
```

## Technologies Used

- **Backend**: FastAPI, Python, SQLAlchemy, Pandas, NumPy
- **Frontend**: React, TypeScript, React Router, Axios
- **Database**: SQLite (default), supports PostgreSQL
- **Analysis**: Statistical analysis with Pandas and NumPy
- **Report Generation**: Custom report builder with natural language generation
- **Authentication**: JWT-based authentication

## Quick Start

### Easiest Way - Use Shell Scripts

```bash
# Start both backend and frontend
./run_server.sh

# Backend will start on: http://localhost:8010
# Frontend will start on: http://localhost:3000
```

### Login Credentials
- **Username**: `admin` | **Password**: `admin123` (Admin)
- **Username**: `tester` | **Password**: `test123` (User)

See [docs/USER_CREDENTIALS.md](docs/USER_CREDENTIALS.md) for complete credentials.

## Latest Updates (v3.0.0)

- ✅ **Performance Comparison Engine**: Automated regression detection
- ✅ **Release Intelligence**: AI-powered release scoring (0-100)
- ✅ **Baseline Management**: Track performance over time
- ✅ **Correlation Analysis**: Backend/Frontend issue detection
- ✅ **Natural Language Reports**: Auto-generated executive summaries
- ✅ **New UI Pages**: Baselines, Compare Runs, Release Decision

## License

MIT License












