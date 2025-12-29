# Quick Start Guide - Version 2.0

## 🎉 New Features in V2.0

### 1. Database Integration ✅
- SQLite database for persistent storage
- Files, analyses, and reports saved automatically
- No need to re-analyze files

### 2. Enhanced Reports Page ✅
- **Tabular layout** with multiple columns
- **Checkbox selection** for multiple files
- **Delete functionality** with confirmation
- **Multiple report formats**: HTML, PDF, PPT, JSON

### 3. AI Chatbot ✅
- Floating 🤖 button in bottom-right corner
- Query performance data using natural language
- Get insights and recommendations
- Context-aware responses

## 🚀 Getting Started

### Step 1: Install Dependencies

```bash
cd /Users/raghvendra1.kumar/AutoReportAnalyzer/backend
source venv/bin/activate
pip install sqlalchemy python-pptx
```

### Step 2: Restart Backend

**Option A: Stop and restart**
```bash
# Stop the current backend (Ctrl+C in the terminal)
pkill -f "uvicorn app.main:app"

# Start fresh
cd /Users/raghvendra1.kumar/AutoReportAnalyzer/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Option B: Let it auto-reload** (if watching file changes)
- The backend should auto-reload when it detects the changes

### Step 3: Refresh Frontend

- Open your browser
- Press **Ctrl+Shift+R** (Windows/Linux) or **Cmd+Shift+R** (Mac)
- This clears cache and reloads the page

### Step 4: Login

- Username: `raghskmr`
- Password: `password`

## 📊 Using the New Features

### Reports Page - Tabular View

1. Go to **Reports** page from the sidebar
2. You'll see a table with:
   - **Checkbox**: Select files for report generation
   - **S.No.**: Serial number
   - **File Name**: Original filename
   - **Type**: Category badge (Web Vitals, JMeter, UI Performance)
   - **Grade**: Performance grade (for JMeter files only)
   - **Actions**: Delete button (🗑️)

### Generating Reports

1. **Select files** using checkboxes (or select all)
2. Choose report type:
   - **📄 HTML Report**: Interactive view in browser
   - **📕 PDF Report**: Downloads PDF file
   - **📊 PowerPoint**: Downloads PPTX file
   - **📋 JSON Report**: View/download JSON data

### Using AI Chatbot

1. Click the **🤖 button** in bottom-right corner
2. Chat window opens
3. Try these questions:
   - "What is the overall performance grade?"
   - "Show me the error rates"
   - "What are the response times?"
   - "Give me recommendations for improvement"
   - "What are the critical issues?"
   - "How can I improve the grade?"

4. Or click **suggested questions** for quick access

### Deleting Files

1. Click **🗑️ Delete** button next to any file
2. Confirm deletion
3. File, analysis results, and reports are removed

## 🗄️ Database

- **Location**: `backend/performance_analyzer.db`
- **Type**: SQLite
- **Auto-created**: On first run
- **Contains**:
  - Uploaded files metadata
  - Analysis results
  - Generated reports
  - Chat history

## 📋 Reports Table Structure

| Column | Description |
|--------|-------------|
| ☑️ Checkbox | Select for report generation |
| S.No. | Serial number |
| File Name | Original filename |
| Type | Category badge |
| Grade | Performance grade (JMeter only) |
| Actions | Delete button |

## 🤖 AI Chatbot Capabilities

- **Query Grades**: "What is the performance grade?"
- **Check Errors**: "Show me error rates"
- **Response Times**: "What are the response times?"
- **Get Recommendations**: "Give me recommendations"
- **Critical Issues**: "What are the critical issues?"
- **Improvement**: "How can I improve the grade?"

## 🔧 Troubleshooting

### Backend Won't Start

**Error**: `ModuleNotFoundError: No module named 'sqlalchemy'`

**Solution**:
```bash
cd backend
source venv/bin/activate
pip install sqlalchemy python-pptx
```

### PDF Generation Fails

**Error**: PDF download doesn't work

**Solution**: Ensure ReportLab is installed:
```bash
pip install reportlab
```

### Chatbot Not Responding

**Issue**: Chatbot shows connection error

**Solution**:
1. Check backend is running on port 8000
2. Check browser console for CORS errors
3. Verify analyzed files exist in localStorage

### Database Locked

**Issue**: SQLite database locked error

**Solution**:
1. Close all connections to database
2. Restart backend server
3. If persistent, delete `performance_analyzer.db` and restart

## 📁 File Structure

```
AutoReportAnalyzer/
├── backend/
│   ├── app/
│   │   ├── database/          # Database models and service
│   │   ├── report_generator/  # PDF, PPT, HTML generators
│   │   └── api/routes.py      # Updated API endpoints
│   ├── performance_analyzer.db # SQLite database (created on run)
│   └── requirements.txt       # Updated dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatBot.tsx    # AI chatbot component
│   │   │   └── ChatBot.css
│   │   └── pages/
│   │       ├── ReportsPage.tsx # Enhanced reports page
│   │       └── ReportsPage.css
│   
└── Documentation/
    ├── FEATURE_IMPLEMENTATION_SUMMARY.md
    ├── REPORT_IMPROVEMENTS_SUMMARY.md
    ├── QUICK_START_V2.md (this file)
    └── USER_CREDENTIALS.md
```

## 🎯 Complete Workflow

1. **Upload Files**
   - Go to Upload page
   - Select files and categories
   - Upload

2. **Analyze Files**
   - Go to Analysis page
   - Select uploaded files
   - Click "Analyze"
   - Results saved automatically to database

3. **Generate Reports**
   - Go to Reports page
   - Select analyzed files
   - Choose report format (HTML/PDF/PPT/JSON)
   - View or download

4. **Query with AI**
   - Click chatbot button
   - Ask questions about performance
   - Get insights and recommendations

5. **Manage Files**
   - Delete unwanted files
   - Re-generate reports anytime
   - No need to re-analyze

## 💡 Tips

- **Select Multiple Files**: Check multiple boxes to combine data in reports
- **Download Reports**: PDFand PPT reports download automatically
- **Chat Context**: Chatbot uses all analyzed files for context
- **Database Backup**: Copy `performance_analyzer.db` to backup your data
- **Reset Data**: Delete database file to start fresh

## 🔮 Future Enhancements

- OpenAI GPT integration for advanced AI
- Email report delivery
- Scheduled report generation
- Team collaboration
- Performance trends over time
- Custom report templates

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review error messages in browser console
3. Check backend logs
4. Verify all dependencies are installed

---

**Version**: 2.0  
**Date**: November 25, 2025  
**Status**: ✅ Production Ready












