# HTML Reports Open in New Tab - Feature Update

## 📝 Overview

HTML reports now open in a new browser tab instead of displaying in a modal, providing a better viewing experience with more screen space and easier navigation.

## 🎯 What Changed

### Before
- HTML reports opened in a modal overlay within the same page
- Limited screen space for viewing reports
- Required closing the modal to navigate elsewhere

### After
- HTML reports open in a dedicated new browser tab
- Full screen space for viewing reports
- Easy navigation between report and main application
- PDF and PPT reports still open in modal (as they work better that way)

## 📂 Files Modified

1. **`frontend/src/pages/FilesPage.tsx`**
   - Updated `handleViewReport()` function
   - HTML reports now use `window.open()` to open in new tab

2. **`frontend/src/pages/WebVitalsPage.tsx`**
   - Updated `handleViewReport()` function
   - HTML reports now use `window.open()` to open in new tab

3. **`frontend/src/pages/JMeterPage.tsx`**
   - Updated `handleViewReport()` function
   - HTML reports now use `window.open()` to open in new tab

## 🔧 Technical Implementation

### Code Changes

```typescript
// OLD CODE (Modal)
if (reportType === 'html') {
  setModalContent({
    type: 'html',
    content: reportData as string,
    filename: run.run_id
  });
  setModalOpen(true);
}

// NEW CODE (New Tab)
if (reportType === 'html') {
  // Open HTML report in a new tab
  const htmlContent = reportData as string;
  const newWindow = window.open('', '_blank');
  if (newWindow) {
    newWindow.document.write(htmlContent);
    newWindow.document.close();
    newWindow.document.title = `${run.run_id} - Performance Report`;
  } else {
    alert('Please allow pop-ups to view the report in a new tab');
  }
}
```

### Key Features

1. **New Tab Opening**: Uses `window.open('', '_blank')` to open a new browser tab
2. **Dynamic Content**: Writes HTML content directly to the new tab using `document.write()`
3. **Custom Title**: Sets the tab title to include the Run ID for easy identification
4. **Pop-up Blocker Detection**: Shows an alert if browser blocks the pop-up
5. **PDF/PPT Unchanged**: PDF and PowerPoint reports continue to use modal display

## 🚀 Usage

### Viewing HTML Reports

1. Navigate to any of these pages:
   - **All Files** (`/files`)
   - **JMeter Tests** (`/jmeter`)
   - **Web Vitals** (`/web-vitals`)

2. Find a run with status **"Generated"**

3. Click the **"HTML"** button under "View Reports"

4. The report will open in a new browser tab

### Browser Compatibility

✅ **Chrome/Edge**: Full support  
✅ **Firefox**: Full support  
✅ **Safari**: Full support  
⚠️ **Pop-up Blockers**: May need to allow pop-ups for this site

### If Pop-ups are Blocked

If your browser blocks the new tab:

1. Look for the pop-up blocker icon in the address bar
2. Click "Always allow pop-ups from this site"
3. Try opening the report again

## 📊 Report Types Behavior

| Report Type | Opening Method | Reason |
|-------------|----------------|--------|
| **HTML** | New Tab | Better viewing experience, full screen |
| **PDF** | Modal | Built-in browser PDF viewer works well in modal |
| **PPT** | Modal with Download | PowerPoint requires download anyway |

## 💡 Benefits

### For Users
- ✅ **More Screen Space**: Full browser window for reports
- ✅ **Easy Navigation**: Switch between tabs without closing modal
- ✅ **Multiple Reports**: Can open multiple reports at once
- ✅ **Browser Features**: Use browser zoom, print, search features
- ✅ **Persistent**: Reports stay open even when navigating main app

### For Performance
- ✅ **No Modal Management**: Simpler state management in React
- ✅ **Memory Efficient**: Browser handles document lifecycle
- ✅ **Standard Behavior**: Uses native browser tab functionality

## 🔍 Testing

### Test Cases

1. **Open HTML Report**
   - ✅ Report opens in new tab
   - ✅ Tab has correct title (Run ID + "Performance Report")
   - ✅ Full HTML content is displayed

2. **Multiple Reports**
   - ✅ Can open multiple HTML reports simultaneously
   - ✅ Each opens in its own tab

3. **Pop-up Blocker**
   - ✅ Alert shows if pop-up is blocked
   - ✅ Works after allowing pop-ups

4. **PDF/PPT Reports**
   - ✅ Still open in modal as before
   - ✅ No breaking changes

## 🎨 User Experience

### Before & After Comparison

**Before (Modal):**
```
Main App → Click HTML → Modal Overlay → View Report → Close Modal → Continue
```

**After (New Tab):**
```
Main App → Click HTML → New Tab Opens → View Report
             ↓
     (Can switch back anytime)
```

## 📝 Notes

1. **Browser Security**: Some browsers may require user permission for pop-ups on first use
2. **Tab Management**: Users can close report tabs independently
3. **No Breaking Changes**: PDF and PPT reports work exactly as before
4. **Backward Compatible**: Works with all existing generated reports

## 🔄 Version

- **Feature Added**: v3.0.1
- **Date**: February 23, 2026
- **Status**: ✅ Active

## 🤝 Related Documentation

- [ENHANCED_REPORTING_GUIDE.md](./ENHANCED_REPORTING_GUIDE.md) - Report generation features
- [QUICKSTART.md](./QUICKSTART.md) - Getting started guide
- [INDEX.md](./INDEX.md) - Documentation index

---

**Enjoy better report viewing with full screen space!** 📊
