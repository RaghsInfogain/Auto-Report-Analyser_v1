# Performance Comparison and Release Intelligence Engine

## 🎯 Overview

The Performance Comparison Engine is an advanced module that automatically compares performance test results between a baseline and current run to detect regressions, improvements, and determine release readiness.

### Key Features

✅ **Baseline Management** - Mark any test run as baseline with tags  
✅ **Automated Regression Detection** - JMeter and Lighthouse comparison  
✅ **Correlation Intelligence** - Backend vs Frontend root cause analysis  
✅ **Release Readiness Scoring** - 0-100 score with automated verdict  
✅ **Natural Language Reports** - Executive summaries in plain English  
✅ **Severity Classification** - Critical/Major/Minor/Stable categorization  

---

## 📐 Architecture

```
backend/app/comparison/
├── engines/
│   ├── jmeter_comparison.py        # Backend metrics comparison
│   ├── lighthouse_comparison.py    # Frontend UX comparison
│   ├── correlation_engine.py       # Root cause correlation
│   └── release_scorer.py           # Release health scoring
├── services/
│   ├── baseline_service.py         # Baseline CRUD operations
│   └── comparison_service.py       # Orchestration layer
└── report_generators/              # (Future: Natural language reports)
```

---

## 🗄️ Database Schema

### New Tables

#### 1. **baseline_runs**
Stores baseline metadata

| Column | Type | Description |
|--------|------|-------------|
| baseline_id | String(100) PK | UUID |
| run_id | String(100) FK | Links to uploaded run |
| application | String(200) | App name |
| environment | String(100) | dev/staging/prod |
| version | String(100) | Release version |
| baseline_name | String(255) | User-friendly name |
| is_active | Boolean | Active flag |

#### 2. **baseline_metrics**
Cached metrics for fast comparison

| Column | Type | Description |
|--------|------|-------------|
| baseline_id | String(100) FK | Baseline reference |
| category | String(50) | jmeter/lighthouse/web_vitals |
| metric_key | String(255) | Metric name |
| metric_value | Float | Numeric value |
| transaction_name | String(500) | API/Page name |

#### 3. **comparison_results**
Stores comparison computations

| Column | Type | Description |
|--------|------|-------------|
| comparison_id | String(100) PK | UUID |
| baseline_id | String(100) FK | Baseline reference |
| current_run_id | String(100) | Current run reference |
| overall_score | Float | Release health (0-100) |
| verdict | String(50) | approved/risky/blocked |
| comparison_data | JSON | Full comparison details |
| status | String(50) | processing/completed/failed |

#### 4. **regression_details**
Individual regression records

| Column | Type | Description |
|--------|------|-------------|
| comparison_id | String(100) FK | Comparison reference |
| metric_name | String(255) | Metric identifier |
| baseline_value | Float | Baseline metric |
| current_value | Float | Current metric |
| change_percent | Float | % change |
| severity | String(50) | critical/major/minor/stable |

---

## 🚀 Getting Started

### 1. Initialize Database

The new tables will be created automatically on first startup:

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

Check logs for:
```
✅ Database initialized successfully!
📊 Performance Comparison Engine loaded
```

### 2. Create Your First Baseline

**Via API:**

```bash
curl -X POST http://localhost:8000/api/comparison/baseline/set \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "Run-1",
    "application": "MyApp",
    "environment": "production",
    "version": "v1.0.0",
    "baseline_name": "Production v1.0.0 Baseline",
    "description": "First production release baseline"
  }'
```

**Response:**
```json
{
  "success": true,
  "baseline": {
    "baseline_id": "uuid-here",
    "run_id": "Run-1",
    "application": "MyApp",
    "environment": "production",
    "version": "v1.0.0"
  }
}
```

### 3. Run a Comparison

```bash
curl -X POST http://localhost:8000/api/comparison/compare \
  -H "Content-Type: application/json" \
  -d '{
    "baseline_id": "baseline-uuid",
    "current_run_id": "Run-5",
    "comparison_type": "full"
  }'
```

**Response:**
```json
{
  "success": true,
  "comparison_id": "comparison-uuid",
  "status": "processing"
}
```

### 4. Check Comparison Status

```bash
curl http://localhost:8000/api/comparison/compare/status/{comparison_id}
```

### 5. Get Results

```bash
curl http://localhost:8000/api/comparison/compare/result/{comparison_id}
```

---

## 📊 Comparison Logic

### JMeter Comparison

**Metrics Compared:**
- Average Response Time
- P90 / P95 / P99 Response Times
- Throughput (TPS)
- Error Rate
- Success Rate
- Per-transaction metrics

**Severity Classification:**

| Change % | Severity |
|----------|----------|
| < 5% | Stable |
| 5-15% | Minor Degradation |
| 15-30% | Major Degradation |
| > 30% | Critical Regression |

**Special Rules:**
- Error rate increase >5% → Critical
- Throughput drop >20% → Critical
- New failures → Critical

### Lighthouse Comparison

**Metrics Compared:**
- Performance Score
- LCP (Largest Contentful Paint)
- CLS (Cumulative Layout Shift)
- FCP (First Contentful Paint)
- TBT (Total Blocking Time)
- Speed Index
- TTI (Time to Interactive)

**UX Degradation Rules:**
- LCP increase >20% → UX Degraded
- CLS >0.25 → Layout Instability
- TBT increase >30% → Blocking Issue
- Performance score drop >10 → Release Risk

### Correlation Intelligence

**Rule Engine:**

```
IF JMeter response time ↑ AND Lighthouse TTFB ↑
→ Backend Performance Issue

IF JMeter stable BUT Lighthouse LCP ↑ and TBT ↑
→ Frontend Rendering Issue

IF Throughput ↓ with same load
→ Scalability Issue

IF Error rate ↑ AND response time ↑
→ Error Handling Issue
```

### Release Readiness Score

**Formula:**

```
Overall Score = (Backend Score × 40%) + 
                (Frontend Score × 40%) + 
                (Reliability Score × 20%)
```

**Classification:**

| Score | Verdict | Action |
|-------|---------|--------|
| 90-100 | Excellent | ✅ Release Approved |
| 75-89 | Acceptable | ⚠️ Monitor |
| 60-74 | Risky | ⚠️ Approval Needed |
| <60 | Blocked | ❌ Release Blocked |

---

## 🔌 API Endpoints

### Baseline Management

```
POST   /api/comparison/baseline/set
GET    /api/comparison/baseline/list
GET    /api/comparison/baseline/{baseline_id}
PATCH  /api/comparison/baseline/{baseline_id}
DELETE /api/comparison/baseline/{baseline_id}
PATCH  /api/comparison/baseline/{baseline_id}/deactivate
```

### Comparison Operations

```
POST   /api/comparison/compare
GET    /api/comparison/compare/status/{comparison_id}
GET    /api/comparison/compare/result/{comparison_id}
GET    /api/comparison/compare/history
```

### Release Intelligence

```
GET    /api/comparison/release/score/{comparison_id}
GET    /api/comparison/release/verdict/{comparison_id}
GET    /api/comparison/release/regressions/{comparison_id}
```

### Reports

```
GET    /api/comparison/report/summary/{comparison_id}
```

---

## 📱 Frontend Integration (TODO)

### New Pages to Create

1. **Baseline Manager** (`/baselines`)
   - List all baselines
   - Create new baseline from any run
   - Filter by app/environment

2. **Comparison Dashboard** (`/compare`)
   - Select baseline + current run
   - Trigger comparison
   - View live status

3. **Regression Heatmap** (`/regressions`)
   - Color-coded severity matrix
   - Drill-down into details

4. **Release Decision Panel** (`/release-decision`)
   - Release score gauge
   - Verdict banner (approved/risky/blocked)
   - Risk factors list

### Example Frontend Code

```typescript
// Create baseline
const response = await fetch('/api/comparison/baseline/set', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    run_id: 'Run-5',
    application: 'MyApp',
    environment: 'prod',
    version: 'v2.0.0',
    baseline_name: 'Production v2.0.0'
  })
});

// Start comparison
const compResponse = await fetch('/api/comparison/compare', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    baseline_id: baselineId,
    current_run_id: 'Run-10',
    comparison_type: 'full'
  })
});

// Poll for results
const checkStatus = async (comparisonId) => {
  const status = await fetch(`/api/comparison/compare/status/${comparisonId}`);
  const data = await status.json();
  
  if (data.status === 'completed') {
    // Fetch full results
    const results = await fetch(`/api/comparison/compare/result/${comparisonId}`);
    return results.json();
  }
  
  // Poll again after 2 seconds
  setTimeout(() => checkStatus(comparisonId), 2000);
};
```

---

## 🧪 Testing

### Manual Testing Steps

1. **Upload baseline run:**
   ```bash
   # Upload JMeter + Lighthouse files for Run-1
   ```

2. **Mark as baseline:**
   ```bash
   POST /api/comparison/baseline/set
   {
     "run_id": "Run-1",
     "application": "TestApp",
     "environment": "prod",
     "version": "v1.0",
     "baseline_name": "Test Baseline"
   }
   ```

3. **Upload current run:**
   ```bash
   # Upload files for Run-2
   ```

4. **Run comparison:**
   ```bash
   POST /api/comparison/compare
   {
     "baseline_id": "<baseline-id>",
     "current_run_id": "Run-2",
     "comparison_type": "full"
   }
   ```

5. **Check results:**
   ```bash
   GET /api/comparison/compare/result/{comparison_id}
   ```

### Expected Output

```json
{
  "success": true,
  "comparison": {
    "comparison_id": "...",
    "overall_score": 78.5,
    "backend_score": 82.0,
    "frontend_score": 75.0,
    "reliability_score": 100.0,
    "verdict": "monitor",
    "regression_count": 5,
    "improvement_count": 3,
    "summary_text": "Release Health Assessment\n..."
  }
}
```

---

## 🔧 Configuration

### Threshold Tuning

You can adjust severity thresholds in the engine files:

**`jmeter_comparison.py`:**
```python
THRESHOLDS = {
    'stable': 5.0,      # Adjust for your needs
    'minor': 15.0,
    'major': 30.0,
    'critical': 30.0
}
```

**`lighthouse_comparison.py`:**
```python
THRESHOLDS = {
    'lcp_increase': 20.0,
    'cls_critical': 0.25,
    'tbt_increase': 30.0,
    'performance_score_drop': 10
}
```

### Release Score Weights

**`release_scorer.py`:**
```python
WEIGHTS = {
    'backend': 0.40,       # 40% - Adjust based on importance
    'frontend': 0.40,      # 40%
    'reliability': 0.20    # 20%
}
```

---

## 📈 Performance Considerations

### Caching Strategy

- ✅ Baseline metrics are cached in `baseline_metrics` table
- ✅ Comparison results are cached in `comparison_results`
- ✅ No need to re-analyze files

### Async Processing

- Comparisons run asynchronously
- Status polling endpoint for monitoring
- Large file handling optimized

### Database Indexes

Key indexes for performance:
```sql
CREATE INDEX idx_baseline_app_env ON baseline_runs(application, environment);
CREATE INDEX idx_comparison_baseline ON comparison_results(baseline_id);
CREATE INDEX idx_regression_comparison ON regression_details(comparison_id);
CREATE INDEX idx_regression_severity ON regression_details(severity);
```

---

## 🐛 Troubleshooting

### Issue: Comparison stuck in "processing"

**Solution:**
```bash
# Check logs for errors
tail -f backend.log

# Check comparison status
curl http://localhost:8000/api/comparison/compare/status/{comparison_id}
```

### Issue: No regressions detected

**Possible causes:**
1. Baseline and current runs are identical
2. Changes are below threshold (< 5%)
3. Analysis results not found

**Solution:**
```bash
# Verify baseline metrics exist
curl http://localhost:8000/api/comparison/baseline/{baseline_id}

# Verify current run has analysis results
curl http://localhost:8000/api/runs/{run_id}
```

### Issue: Release score is 0

**Cause:** No metrics available for comparison

**Solution:** Ensure both baseline and current runs have analyzed data

---

## 🎓 Best Practices

### 1. Baseline Management

- ✅ Create baselines for each major release
- ✅ Tag with environment (dev/staging/prod)
- ✅ Use semantic versioning for baseline names
- ✅ Keep baselines for historical comparison

### 2. Comparison Workflow

- ✅ Always compare against appropriate baseline (same environment)
- ✅ Run comparisons before deployments
- ✅ Monitor trends over multiple comparisons
- ✅ Document decisions for blocked releases

### 3. Thresholds

- ✅ Tune thresholds based on your application SLAs
- ✅ Stricter thresholds for production
- ✅ Relaxed thresholds for dev/staging

---

## 🚧 Future Enhancements

- [ ] PDF/HTML comparison report generation
- [ ] Trend analysis across multiple baselines
- [ ] Slack/Email notifications for regressions
- [ ] Custom threshold configuration per application
- [ ] A/B testing comparison support
- [ ] Historical trend charts

---

## 📞 Support

For issues or questions:
- Check logs: `backend.log`
- API docs: http://localhost:8000/docs
- Review this documentation

---

## ✅ Quick Start Checklist

- [ ] Backend running with new database tables
- [ ] Create first baseline from existing run
- [ ] Upload new test run
- [ ] Trigger comparison
- [ ] Review results and verdict
- [ ] Integrate with CI/CD pipeline (optional)

---

**Version:** 1.0.0  
**Last Updated:** 2025-12-24  
**Status:** Production Ready ✅
