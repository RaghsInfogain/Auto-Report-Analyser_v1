# Sample Data Files

This directory contains sample data files for testing the Auto Report Analyzer application.

## Files

### 1. web_vitals_sample.json
Sample Web Vitals data with Core Web Vitals metrics:
- LCP (Largest Contentful Paint)
- FID (First Input Delay)
- CLS (Cumulative Layout Shift)
- FCP (First Contentful Paint)
- TTFB (Time to First Byte)
- INP (Interaction to Next Paint)

### 2. jmeter_sample.csv
Sample JMeter test results in CSV format with:
- Response times
- Latency measurements
- Success/failure status
- Response codes
- Thread information

### 3. ui_performance_sample.json
Sample UI Performance data with Navigation Timing metrics:
- DNS lookup time
- Connection time
- SSL/TLS time
- Time to First Byte
- Page load times
- DOM processing time

## Usage

1. Start the backend and frontend servers
2. Upload these files through the UI
3. Assign appropriate categories:
   - `web_vitals_sample.json` → Web Vitals
   - `jmeter_sample.csv` → JMeter Test Results
   - `ui_performance_sample.json` → UI Performance
4. Click "Analyze Selected Files"
5. Click "Generate Comprehensive Report"












