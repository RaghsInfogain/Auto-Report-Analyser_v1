# Auto Report Analyzer

A comprehensive performance analysis application for analyzing Web Vitals, JMeter test results, and UI Performance metrics.

## Features

- **Multi-format Support**: Upload JSON, CSV, and JTL files
- **Three Analysis Categories**:
  - Web Vitals (LCP, FID, CLS, FCP, TTFB, INP)
  - JMeter Test Results (latency, throughput, error rates)
  - UI Performance (DNS lookup, connection time, page load time)
- **Comprehensive Reports**: Generate detailed performance reports with recommendations
- **Statistical Analysis**: Mean, median, P95, P99 metrics
- **Modern UI**: React-based frontend with TypeScript

## Project Structure

```
AutoReportAnalyzer/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── models/         # Data models
│   │   ├── parsers/        # File parsers (JSON, CSV, JTL)
│   │   ├── analyzers/      # Analysis logic
│   │   ├── report_generator/ # Report generation
│   │   └── api/            # API routes
│   ├── requirements.txt
│   └── uploads/            # Uploaded files storage
└── frontend/               # React frontend
    ├── src/
    │   ├── components/     # React components
    │   └── services/       # API services
    └── package.json
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
uvicorn app.main:app --reload --port 8000
```

The backend API will be available at `http://localhost:8000`

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
| `run_server.bat` | Start both backend and frontend (opens two windows). Backend: http://localhost:8000, Frontend: http://localhost:3020 |
| `start_backend.bat` | Backend only (FastAPI on port 8000) |
| `start_frontend.bat` | Frontend only (React on port 3020) |
| `run_backend.bat` | Backend only, with venv setup and dependency check |
| `run_frontend.bat` | Frontend only, with npm install if needed |
| `restart_standard_ports.bat` | Stop processes on ports 6000, 7001, 8000, 3000, 3020 and restart backend and frontend |
| `migrate_to_sequential_runs.bat` | Run the Run ID migration script (requires backend venv) |

**Prerequisites on Windows:** Python 3 (or `py -3`), Node.js/npm. Double-click a `.bat` file or run it from Command Prompt.

## Usage

1. **Upload Files**: Select multiple files and assign categories (Web Vitals, JMeter, UI Performance)
2. **Analyze**: Select uploaded files and click "Analyze Selected Files"
3. **Generate Report**: Click "Generate Comprehensive Report" to create a detailed performance report

## API Endpoints

- `POST /api/upload` - Upload files with categories
- `GET /api/files` - List all uploaded files
- `POST /api/analyze` - Analyze selected files
- `POST /api/report/generate` - Generate comprehensive report
- `GET /api/health` - Health check

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

- **Backend**: FastAPI, Python, Pandas, NumPy
- **Frontend**: React, TypeScript, Axios
- **Analysis**: Statistical analysis with Pandas and NumPy
- **Report Generation**: Custom report builder

## License

MIT License












