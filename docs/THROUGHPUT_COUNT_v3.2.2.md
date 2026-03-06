# Throughput Graph Update - v3.2.2
## Sample Count Over Time by Transaction vs VUsers

**Date:** March 6, 2026  
**Version:** 3.2.2  
**Type:** Enhancement

---

## Overview

Updated the throughput graph to display **raw sample counts** instead of calculated throughput rates (req/s), providing clearer insights into transaction execution patterns over time.

---

## Changes Made

### 1. Data Calculation Update
**File:** `backend/app/analyzers/jmeter_analyzer_v2.py`

Changed the throughput calculation in time series data from rate-based to count-based:

**Before:**
```python
"throughput": round(label_total / interval_size, 2) if interval_size > 0 else 0.0
```

**After:**
```python
"throughput": label_count,  # Use raw count instead of rate
```

### 2. Graph Title Update
**File:** `backend/app/report_generator/html_report_generator.py`

**Before:**
```
📈 Throughput Over Time by Transaction vs VUsers
```

**After:**
```
📈 Sample Count Over Time by Transaction vs VUsers
```

### 3. Graph Description Update
**Before:**
```
Throughput trends for transactions/requests over time compared with virtual user load.
```

**After:**
```
Number of samples (executions) for each transaction controller over time, compared with virtual user load.
```

### 4. Y-Axis Label Update
**Before:**
```javascript
title: { display: true, text: 'Throughput (req/s)' }
```

**After:**
```javascript
title: { display: true, text: 'Sample Count' }
```

### 5. Table Display Format Update
Changed table cell formatting to display integers instead of decimals:

**Before:**
```python
row_cells += f'<td ...>{tp:.2f}</td>'  # Shows: 3.45
```

**After:**
```python
row_cells += f'<td ...>{int(tp)}</td>'  # Shows: 3
```

---

## Benefits

### 1. **Clearer Transaction Execution Visibility**
- Shows exactly how many times each transaction controller executed in each time interval
- Easier to identify execution patterns and sequences

### 2. **Better Flow Analysis**
- Integer counts make it clear when transactions are executed 0, 1, 2, or more times
- Helps identify transaction execution frequency patterns

### 3. **Improved Data Interpretation**
- No confusion between "rate" and "count"
- More intuitive for understanding transaction controller behavior

### 4. **Consistent with Filtering Logic**
- Works seamlessly with existing URL=NULL filtering (transaction controllers)
- Falls back to URL!=NULL (requests) when no transaction controllers exist

---

## Example Output

### Run-11 (Virgin Australia)
**Transaction Controllers:** 6 labels (T100, T200, T300, T400, T500, T600)
**Sample Data:**
- T100_Launch: 1 execution at 00:14:00, 1 at 00:14:58, 1 at 00:18:12, etc.
- T200_Flights_To: 1 execution at 00:02:39, 1 at 00:09:23, etc.

### Run-2 (DHR System)
**Transaction Controllers:** 13 labels (TC01, TC02, TC03, TC04...)
**Sample Data:**
- TC01_ASPIRE_Launch: 1 execution at 00:21:41, 1 at 00:49:36
- TC02_ATS_Login: 1 execution at 00:46:06, 1 at 01:03:48, 1 at 01:04:36
- TC02_DHR_Login: 1 execution at 00:10:22, 1 at 01:16:43

---

## Technical Details

### Data Flow
1. **Parser** (`jtl_parser_v2.py`): Extracts URL field from JTL files
2. **Analyzer** (`jmeter_analyzer_v2.py`): 
   - Determines transaction controllers (URL=NULL or "Number of samples in transaction")
   - Calculates count per label per time interval
   - Sets `has_url` flag for filtering
3. **Generator** (`html_report_generator.py`):
   - Filters labels (prioritizes transaction controllers)
   - Renders line graph with integer counts
   - Displays data table with integer values

### Graph Configuration
- **Type:** Scatter with `showLine: true` (line graph)
- **Line Style:** Smooth curves (`tension: 0.3`)
- **Point Display:** Small points (`pointRadius: 3`)
- **Fill:** No area fill (`fill: false`)
- **Transparency:** 20% background color opacity

---

## Verification Results

Both Run-11 and Run-2 reports successfully verified:
- ✓ Title updated correctly
- ✓ Y-axis label updated correctly
- ✓ Data shows integer counts (1, 2, 3, etc.)
- ✓ Transaction controller filtering working correctly
- ✓ Line graphs rendering properly
- ✓ Table displays match graph data

---

## Files Modified

1. `backend/app/analyzers/jmeter_analyzer_v2.py` - Changed throughput calculation
2. `backend/app/report_generator/html_report_generator.py` - Updated graph title, labels, and formatting

---

## Related Documentation

- [Transaction Sorting v3.1.0](./TRANSACTION_SORTING_v3.1.0.md) - Natural sorting for transaction flow
- [Graph Filtering v3.2.0](./GRAPH_FILTERING_v3.2.0.md) - URL-based transaction controller filtering
- [Graph Visualization v3.2.1](./GRAPH_VISUALIZATION_v3.2.1.md) - Line graph rendering

---

**Status:** ✅ Complete and Verified  
**Pushed to GitHub:** ✅ Yes (Commit: d45c25c)
