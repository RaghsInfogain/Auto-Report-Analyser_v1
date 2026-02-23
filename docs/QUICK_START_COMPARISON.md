# 🚀 Quick Start: Performance Comparison Engine

## 5-Minute Setup Guide

---

### Step 1: Database Migration (1 minute)

```bash
cd /Users/raghvendra1.kumar/AutoReportAnalyzer/backend
source venv/bin/activate
python migrate_comparison_tables.py
```

**Expected Output:**
```
✅ Created table: baseline_runs
✅ Created table: baseline_metrics
✅ Created table: comparison_results
✅ Created table: regression_details
```

---

### Step 2: Restart Backend (30 seconds)

**Option A: Using existing terminal**
- Stop current backend (Ctrl+C)
- Restart: `uvicorn app.main:app --reload --port 8000`

**Option B: Using run script**
```bash
cd /Users/raghvendra1.kumar/AutoReportAnalyzer
./run_backend.sh
```

**Verify:**
```
✅ Database initialized successfully!
📊 Performance Comparison Engine loaded
```

---

### Step 3: Test API (2 minutes)

**Open API Docs:**
```
http://localhost:8000/docs
```

Look for new section: **"Performance Comparison"** with 14 endpoints.

---

### Step 4: Create First Baseline (1 minute)

Assuming you have an existing run (e.g., "Run-1"):

```bash
curl -X POST http://localhost:8000/api/comparison/baseline/set \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "Run-1",
    "application": "MyApp",
    "environment": "production",
    "version": "v1.0.0",
    "baseline_name": "Production Baseline v1.0.0",
    "description": "Initial production baseline"
  }'
```

**Response:**
```json
{
  "success": true,
  "baseline": {
    "baseline_id": "abc-123-...",
    "run_id": "Run-1",
    "...": "..."
  }
}
```

**Save the `baseline_id` for next step!**

---

### Step 5: Run Comparison (1 minute)

Assuming you have a newer run (e.g., "Run-5"):

```bash
curl -X POST http://localhost:8000/api/comparison/compare \
  -H "Content-Type: application/json" \
  -d '{
    "baseline_id": "YOUR-BASELINE-ID-HERE",
    "current_run_id": "Run-5",
    "comparison_type": "full"
  }'
```

**Response:**
```json
{
  "success": true,
  "comparison_id": "xyz-456-...",
  "status": "processing"
}
```

---

### Step 6: Get Results (30 seconds)

**Check Status:**
```bash
curl http://localhost:8000/api/comparison/compare/status/{comparison_id}
```

**Get Full Results:**
```bash
curl http://localhost:8000/api/comparison/compare/result/{comparison_id}
```

**Get Release Verdict:**
```bash
curl http://localhost:8000/api/comparison/release/verdict/{comparison_id}
```

---

## ✅ You're Done!

The Performance Comparison Engine is now fully operational.

---

## 🎯 What You Can Do Now

### Via API

1. **List all baselines**
   ```bash
   curl http://localhost:8000/api/comparison/baseline/list
   ```

2. **Filter baselines**
   ```bash
   curl "http://localhost:8000/api/comparison/baseline/list?application=MyApp&environment=production"
   ```

3. **View comparison history**
   ```bash
   curl http://localhost:8000/api/comparison/compare/history
   ```

4. **Get regressions by severity**
   ```bash
   curl "http://localhost:8000/api/comparison/release/regressions/{comparison_id}?severity=critical"
   ```

5. **Get executive summary**
   ```bash
   curl http://localhost:8000/api/comparison/report/summary/{comparison_id}
   ```

### Via Swagger UI

1. Go to http://localhost:8000/docs
2. Scroll to **"Performance Comparison"** section
3. Click "Try it out" on any endpoint
4. Fill parameters and execute

---

## 📊 Understanding Results

### Release Score (0-100)

- **90-100**: ✅ **Release Approved** - No issues
- **75-89**: ⚠️ **Monitor** - Minor concerns
- **60-74**: ⚠️ **Approval Needed** - Significant issues
- **<60**: ❌ **Release Blocked** - Critical issues

### Verdict Types

- `approved` - Safe to release
- `monitor` - Release with caution
- `approval_needed` - Need stakeholder approval
- `blocked` - Do not release

### Severity Levels

- `critical` - Must be fixed before release
- `major` - Should be investigated
- `minor` - Can be monitored
- `stable` - No significant change
- `improvement` - Performance improved

---

## 🔥 Common Use Cases

### 1. Pre-Release Check

```bash
# Before deploying to production
BASELINE_ID="prod-baseline-id"
CURRENT_RUN="Run-latest"

curl -X POST http://localhost:8000/api/comparison/compare \
  -H "Content-Type: application/json" \
  -d "{
    \"baseline_id\": \"$BASELINE_ID\",
    \"current_run_id\": \"$CURRENT_RUN\",
    \"comparison_type\": \"full\"
  }"

# Wait for completion
# Check verdict
# Proceed or block based on result
```

### 2. Compare Only Backend

```bash
curl -X POST http://localhost:8000/api/comparison/compare \
  -H "Content-Type: application/json" \
  -d '{
    "baseline_id": "YOUR-BASELINE-ID",
    "current_run_id": "Run-X",
    "comparison_type": "jmeter"
  }'
```

### 3. Compare Only Frontend

```bash
curl -X POST http://localhost:8000/api/comparison/compare \
  -H "Content-Type: application/json" \
  -d '{
    "baseline_id": "YOUR-BASELINE-ID",
    "current_run_id": "Run-X",
    "comparison_type": "lighthouse"
  }'
```

---

## 🐛 Troubleshooting

### Issue: "Baseline not found"

**Solution:** Verify baseline exists
```bash
curl http://localhost:8000/api/comparison/baseline/list
```

### Issue: "Run not found"

**Solution:** Verify run exists
```bash
curl http://localhost:8000/api/runs
```

### Issue: "Comparison stuck in processing"

**Solution:** Check backend logs
```bash
tail -f backend.log
```

### Issue: "No metrics found"

**Cause:** Run hasn't been analyzed yet  
**Solution:** Analyze the run first, then create baseline/compare

---

## 📚 Next Steps

### Option 1: Build UI (Frontend Integration)

Create these pages:
1. Baseline Manager (`/baselines`)
2. Comparison Dashboard (`/compare`)
3. Release Decision Panel (`/release-decision`)

See `PERFORMANCE_COMPARISON_README.md` for UI examples.

### Option 2: CI/CD Integration

Add to your pipeline:
```yaml
- name: Run Performance Tests
  run: ./run_tests.sh

- name: Compare with Baseline
  run: |
    COMPARISON_ID=$(curl -X POST ... | jq -r '.comparison_id')
    VERDICT=$(curl .../verdict/$COMPARISON_ID | jq -r '.verdict')
    if [ "$VERDICT" == "blocked" ]; then
      echo "Release blocked due to performance regression"
      exit 1
    fi
```

### Option 3: Notifications

Set up webhooks to trigger on comparisons:
- Slack alerts for critical regressions
- Email reports for completed comparisons
- Dashboard integrations

---

## 📖 Documentation

- **Architecture**: `PERFORMANCE_COMPARISON_ARCHITECTURE.md`
- **Full Guide**: `PERFORMANCE_COMPARISON_README.md`
- **Implementation**: `COMPARISON_ENGINE_IMPLEMENTATION_SUMMARY.md`
- **API Docs**: http://localhost:8000/docs

---

## ✅ Success Checklist

- [ ] Database migration completed
- [ ] Backend restarted successfully
- [ ] API docs accessible
- [ ] First baseline created
- [ ] First comparison executed
- [ ] Results retrieved successfully
- [ ] Understand release scores
- [ ] Know how to interpret verdicts

---

## 🎉 You're All Set!

The Performance Comparison Engine is ready for production use.

**Questions?** Check the documentation or API docs.

**Ready to integrate?** Start with the baseline manager UI.

---

**Happy Testing! 🚀**
