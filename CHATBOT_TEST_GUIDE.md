# AI Chatbot - Quick Test Guide

## 🚀 How to Test the AI Chatbot

### Prerequisites:
- ✅ Backend running on `http://localhost:8000`
- ✅ Frontend running on `http://localhost:3000`
- ✅ At least one JMeter file uploaded and analyzed

---

## Step-by-Step Testing

### 1. Open the Application
```
http://localhost:3000
```
Login with:
- Username: `raghskmr`
- Password: `password`

### 2. Upload & Analyze a JMeter File
1. Go to **Upload** page
2. Upload a `.jtl` file
3. Go to **Analysis** page
4. Click **Analyze** on your file
5. Wait for analysis to complete

### 3. Open the Chatbot
Click the **🤖** button in the bottom-right corner

### 4. Test Sample Prompts

**Try these Quick Questions (click them):**
1. "What's the overall performance grade?"
2. "Show me the error rates"
3. "What are the response times?"
4. "Give me recommendations"
5. "What are the critical issues?"
6. "Compare current vs targets"

**Expected Result:**
- Bot should respond with detailed, formatted analysis
- Response should include metrics, grades, and insights
- Should see icons (✅⚠️❌) for status

### 5. Test Categories

Click **"📚 View All Sample Questions"** to see:
- 📊 Overview & Summary
- ⚡ Response Times
- ❌ Errors & Failures
- 🔴 Critical Issues
- 💡 Recommendations
- 📈 Comparisons
- 💰 Business Impact
- 📊 Specific Metrics
- 🎯 Trends & Patterns

**Test:** Click any prompt from each category

### 6. Test Custom Questions

Type these questions manually:

**Test 1: Overview**
```
What's the overall grade?
```
**Expected:** Grade, score, breakdown

**Test 2: Response Times**
```
Show me all percentile data
```
**Expected:** 70th, 80th, 90th, 95th, 99th percentiles

**Test 3: Errors**
```
What's the error rate?
```
**Expected:** Error count, rate, response codes

**Test 4: Endpoints**
```
Show me the worst performing transactions
```
**Expected:** Top 5 slowest with metrics

**Test 5: Recommendations**
```
How can I improve performance?
```
**Expected:** Categorized recommendations with priorities

**Test 6: Business Impact**
```
What's the business impact?
```
**Expected:** Cost analysis, ROI, payback period

**Test 7: Comparison**
```
Compare current vs target metrics
```
**Expected:** Table with current, target, status

**Test 8: SLA**
```
Are we meeting SLA requirements?
```
**Expected:** SLA compliance percentages

---

## Example Expected Responses

### Test: "What's the overall performance grade?"

**Expected Response:**
```
🎯 Performance Grade Analysis

📁 load_test.jtl

Overall Grade: C+ (67/100)

Detailed Scores:
• ⚡ Performance: 50/100
• 🛡️ Reliability: 80/100
• 👥 User Experience: 55/100
• 📈 Scalability: 65/100

Score Breakdown:
• Availability: 98/100
• Response Time: 45/100
• Error Rate: 90/100
...
```

### Test: "Show me the error rates"

**Expected Response:**
```
❌ Error Rate Analysis

📁 load_test.jtl

Error Statistics:
• Total Errors: 28,252
• Total Requests: 1,398,638
• Error Rate: 2.02%
• Success Rate: 97.98%

Response Code Distribution:
✅ 200: 1,351,284 (96.61%)
✅ 201: 19,062 (1.36%)
⚠️ 400: 5,611 (0.40%)
❌ 500: 11,185 (0.80%)
...
```

### Test: "How can I improve performance?"

**Expected Response:**
```
💡 Performance Improvement Recommendations

📁 load_test.jtl

Performance (Priority: High)
• Implement database query optimization
• Add Redis caching layer
• Optimize API endpoints
...

Reliability (Priority: Critical)
• Root cause analysis of failing endpoints
• Implement circuit breakers
...
```

---

## UI Testing

### Visual Checks:
- ✅ Chatbot button is visible (bottom-right)
- ✅ Badge shows number of analyzed files
- ✅ Window opens smoothly
- ✅ Header shows "Performance AI Assistant"
- ✅ Sample prompts are organized
- ✅ Typing indicator appears when processing
- ✅ Messages are properly formatted
- ✅ Icons display correctly (✅⚠️❌📊💡)
- ✅ Context info shows file count

### Interaction Checks:
- ✅ Click prompts to send them
- ✅ Type manually and press Enter
- ✅ Clear chat button works
- ✅ Toggle prompts button works
- ✅ Scroll works in messages area
- ✅ Close button closes window
- ✅ Reopen preserves chat history

---

## API Testing

### Test Sample Prompts Endpoint:
```bash
curl http://localhost:8000/api/chat/sample-prompts
```

**Expected:** JSON with `all_prompts` and `suggested_prompts`

### Test Chat Endpoint:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the overall grade?",
    "session_id": "test-session",
    "file_ids": ["<your-file-id>"]
  }'
```

**Expected:** JSON with `response`, `intent`, `context_files`

---

## Troubleshooting

### Issue: Chatbot button not visible
**Fix:**
1. Check frontend console for errors
2. Verify ChatBot.tsx is imported in Layout.tsx
3. Check CSS is loading

### Issue: No response from chatbot
**Fix:**
1. Check backend is running: `curl http://localhost:8000/api/health`
2. Check browser console for network errors
3. Verify file is analyzed

### Issue: Sample prompts not loading
**Fix:**
1. Check `/api/chat/sample-prompts` endpoint
2. Should see fallback prompts if endpoint fails
3. Check network tab for 404/500 errors

### Issue: Response says "No Analysis Data"
**Fix:**
1. Upload a JMeter file
2. Go to Analysis page and analyze it
3. Wait for analysis to complete
4. File should appear in context info

### Issue: Formatting looks broken
**Fix:**
1. Check ChatBot.css is loaded
2. Clear browser cache
3. Check for CSS conflicts

---

## Performance Testing

### Test with Multiple Files:
1. Upload and analyze 3-5 files
2. Badge should show correct count
3. Context info should show all files
4. Responses should aggregate data

### Test Long Conversations:
1. Ask 10+ questions
2. Scroll should work smoothly
3. Clear chat should work
4. No memory leaks

### Test Large Responses:
1. Ask "Give me an overview"
2. Response should be complete
3. Formatting should remain intact
4. No truncation

---

## Automated Testing Script

Save as `test_chatbot.sh`:

```bash
#!/bin/bash

echo "Testing AI Chatbot..."

# Test health
echo "1. Testing backend health..."
curl -s http://localhost:8000/api/health | grep -q "healthy" && echo "✅ Backend healthy" || echo "❌ Backend down"

# Test sample prompts
echo "2. Testing sample prompts..."
curl -s http://localhost:8000/api/chat/sample-prompts | grep -q "overview" && echo "✅ Sample prompts working" || echo "❌ Prompts failed"

# Test chat (requires file_id)
echo "3. Testing chat endpoint..."
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"test","file_ids":[]}' | grep -q "response" && echo "✅ Chat endpoint working" || echo "❌ Chat failed"

echo "Testing complete!"
```

Run:
```bash
chmod +x test_chatbot.sh
./test_chatbot.sh
```

---

## Checklist

### Backend:
- [ ] `/api/chat/sample-prompts` returns prompts
- [ ] `/api/chat` accepts POST requests
- [ ] Intent detection works
- [ ] Responses are formatted
- [ ] Context data is used
- [ ] Chat history saves to DB

### Frontend:
- [ ] Chatbot button visible
- [ ] Badge shows file count
- [ ] Window opens/closes
- [ ] Sample prompts display
- [ ] Quick questions work
- [ ] Categories expand/collapse
- [ ] Messages display correctly
- [ ] Typing indicator shows
- [ ] Clear chat works
- [ ] Context info accurate

### Integration:
- [ ] Frontend calls backend API
- [ ] Responses render properly
- [ ] Icons display (✅⚠️❌)
- [ ] Tables format correctly
- [ ] Multi-file context works
- [ ] Error handling works

---

## Success Criteria

✅ **All sample prompts load**
✅ **Responses are intelligent and relevant**
✅ **Formatting includes icons and tables**
✅ **UI is responsive and smooth**
✅ **No console errors**
✅ **Chat history persists**
✅ **Multi-file analysis works**

---

## Next Steps After Testing

1. **Test with real JMeter data**
2. **Try edge cases** (no data, malformed queries)
3. **Test on different browsers**
4. **Check mobile responsiveness**
5. **Verify database storage**
6. **Test long conversations**

---

**Happy Testing! 🎉**

Report any issues or suggestions for improvement.












