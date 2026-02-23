# Quick Start Guide

## Prerequisites

- Python 3.8 or higher
- Node.js 14 or higher
- npm or yarn

## Installation & Setup

### Option 1: Using Quick Start Scripts (Recommended)

#### Terminal 1 - Start Backend
```bash
cd /Users/raghvendra1.kumar/AutoReportAnalyzer
./start_backend.sh
```

#### Terminal 2 - Start Frontend
```bash
cd /Users/raghvendra1.kumar/AutoReportAnalyzer
./start_frontend.sh
```

### Option 2: Manual Setup

#### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### Frontend Setup
```bash
cd frontend
npm install
npm start
```

## Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Test with Sample Data

1. Navigate to http://localhost:3000
2. Use the sample files in the `sample_data/` directory:
   - `web_vitals_sample.json` (Category: Web Vitals)
   - `jmeter_sample.csv` (Category: JMeter Test Results)
   - `ui_performance_sample.json` (Category: UI Performance)
3. Upload all three files
4. Select all uploaded files
5. Click "Analyze Selected Files"
6. Click "Generate Comprehensive Report"

## Workflow

1. **Upload Files**
   - Click "Choose File" and select one or more files
   - Assign the appropriate category to each file
   - Click "Upload Files"

2. **Analyze Data**
   - Check the boxes next to the files you want to analyze
   - Click "Analyze Selected Files"
   - View individual analysis results for each file

3. **Generate Report**
   - Select the analyzed files you want in the report
   - Click "Generate Comprehensive Report"
   - View the comprehensive report with recommendations

## File Format Support

### Web Vitals
- **Formats**: JSON, CSV
- **Required Fields**: lcp, fid, cls, fcp, ttfb
- **Optional Fields**: inp, url, timestamp

### JMeter Test Results
- **Formats**: JTL (CSV or XML)
- **Required Fields**: elapsed/sample_time, label, responseCode
- **Optional Fields**: latency, success, threadName, bytes

### UI Performance
- **Formats**: JSON, CSV
- **Required Fields**: dns_lookup_time, connection_time, page_load_time
- **Optional Fields**: ssl_time, ttfb, dom_processing_time, full_page_load_time

## API Endpoints

- `POST /api/upload` - Upload files
- `GET /api/files` - List uploaded files
- `POST /api/analyze` - Analyze files
- `POST /api/report/generate` - Generate report
- `GET /api/health` - Health check

## Troubleshooting

### Backend Issues
- **Port already in use**: Change the port in start_backend.sh
- **Module not found**: Ensure you're in the venv and dependencies are installed
- **Import errors**: Check that all __init__.py files exist

### Frontend Issues
- **Port 3000 in use**: The app will prompt to use a different port
- **API connection failed**: Ensure backend is running on port 8000
- **Module not found**: Run `npm install` in the frontend directory

### File Upload Issues
- **File format not supported**: Check file extension and category match
- **Analysis failed**: Verify file format matches the expected structure
- **No data**: Ensure the file contains valid data in the correct format

## Next Steps

- Customize the report template in `backend/app/report_generator/report_builder.py`
- Add visualization charts using matplotlib/seaborn
- Implement database storage for file metadata
- Add user authentication
- Deploy to production server

## Support

For issues or questions, refer to the main README.md file.












