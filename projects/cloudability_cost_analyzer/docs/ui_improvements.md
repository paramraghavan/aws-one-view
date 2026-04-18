# Dashboard UI Improvements: Dynamic Tabs & Sidebar

New dashboard features for better report management and navigation.

---

## Overview

The dashboard now features:
1. **Left sidebar** with all available reports
2. **Dynamic tab management** - open/close tabs as needed
3. **Auto-detected filters** from SQL queries
4. **Better organization** when working with multiple reports

---

## Feature 1: Left Sidebar with Report List

### What Changed
- Left sidebar shows all available reports from `config/tabs.yaml`
- Click any report to open it as a new tab
- Sidebar highlights the currently active tab
- Responsive design - sidebar moves below tabs on mobile

### How to Use
```
1. Open the dashboard
2. See all reports listed in left sidebar
3. Click a report name to open it
4. Report opens as a new tab in the tab bar
```

### Styling
- **Color scheme:** Dark sidebar (#2c3e50) with white text
- **Hover effect:** Highlights in light blue on hover
- **Active state:** Bright blue (#1E90FF) for active report
- **Icons:** Report emoji (📊) for quick visual scanning

---

## Feature 2: Dynamic Tab Management

### What Changed
- Tabs are now created **on-demand** when you click a report
- Multiple tabs can be **open simultaneously**
- Each tab has a **close (×) button**
- At least one tab must always remain open

### How to Use
```
1. Click a report in sidebar → new tab opens
2. Click another report → another tab opens
3. Click × on any tab → closes that tab
4. Tabs preserve their state when switched
```

### Tab Operations
- **Open:** Click report name in sidebar
- **Switch:** Click tab button in tab bar
- **Close:** Click × button on tab
- **Prevent single tab closure:** Alert if only one tab remains

### Example Workflow
```
Before:  [Cost by VP] [Top Users] [Service Costs]  ← All pre-rendered
After:   (sidebar shows all 6 reports)
         [Cost by VP] [Top Users]  ← Click to open more
```

---

## Feature 3: Auto-Detected Filters from SQL

### What Changed
- Filters are now **automatically generated** from SQL columns
- No need to manually define filters in config
- Filters appear **dynamically** when data loads

### How to Use
```
1. Dashboard opens a report
2. SQL query is analyzed
3. Columns are extracted from SELECT clause
4. Filter dropdowns are created
5. Select filter values → chart updates
```

### Filter Detection
Extracts columns from SQL queries:
- ✅ Simple columns: `SELECT column FROM table`
- ✅ Aggregates: `SELECT SUM(amount) as total`
- ✅ Aliases: `SELECT amount AS cost`
- ✅ Functions: `SELECT COUNT(id) FROM users`

### Example SQL → Auto-Detected Filters
```sql
SELECT
  block_funding,
  state,
  SUM(total_cost) as total,
  COUNT(DISTINCT user_id) as users
FROM cost_report c
JOIN regions r ON c.user_id = r.user_id
GROUP BY block_funding, state
```

**Auto-generates filters for:**
- block_funding
- state
- total
- users

### Filter UI
- **Dropdown format:** Select from distinct values
- **"All" option:** First option to show all data
- **Reset button:** Clear all filters at once
- **Responsive:** Full-width on mobile

---

## Technical Changes

### File Modifications

#### 1. templates/dashboard.html
**Changes:**
- Removed server-side tab rendering
- Added sidebar with report list
- Added dynamic tab container
- Changed layout from single column to sidebar + main

**Key Sections:**
```html
<!-- Sidebar with report list -->
<aside class="sidebar">
  <div class="reports-list">
    {% for tab in tabs %}
      <div class="report-item" data-report-id="{{ tab.id }}">
```

#### 2. static/css/style.css
**Changes:**
- Added `.dashboard-layout` for flex layout
- Added `.sidebar` styles (280px dark panel)
- Updated `.tab-button` to support close button
- Added responsive breakpoints for mobile
- Added `.tab-close` button styling

**New Styles:**
```css
.dashboard-layout { display: flex; flex: 1; }
.sidebar { width: 280px; background: #2c3e50; }
.report-item { padding: 12px 20px; cursor: pointer; }
.tab-close { color: #999; cursor: pointer; }
```

#### 3. static/js/dashboard.js
**Changes:**
- Replaced static tab initialization with dynamic management
- Added `openTabs` Map for state management
- Added functions: `openReport()`, `createTab()`, `closeTab()`
- Added `detectAndRenderFilters()` for auto-detection
- Added `extractColumnsFromSQL()` to parse SQL
- Added `renderAutoDetectedFilters()` to create filter UI

**New Functions:**
- `initializeDashboard()` - Setup sidebar and open first report
- `openReport(reportId)` - Open or switch to report
- `createTab(reportId)` - Create new tab dynamically
- `closeTab(reportId)` - Remove tab (prevent last one)
- `switchToTab(reportId)` - Switch active tab
- `detectAndRenderFilters(tabId)` - Auto-detect filters
- `extractColumnsFromSQL(sql)` - Parse SQL for columns
- `renderAutoDetectedFilters(tabId, columns)` - Create filter UI

#### 4. reporting_engine.py
**Changes:**
- Added `/api/config/<tab_id>` endpoint
- Returns SQL and metadata for auto-detect feature

**New Endpoint:**
```python
@app.route('/api/config/<tab_id>')
def get_tab_config(tab_id):
    # Returns name, description, sql, chart, filters
```

---

## User Experience Flow

### Opening the Dashboard
```
1. Load http://localhost:5445
2. Dashboard renders header + sidebar
3. Sidebar shows all available reports
4. First report auto-opens as initial tab
5. Filters auto-detect from SQL
```

### Managing Reports
```
1. Click report in sidebar
   └─ If not open: Creates new tab
   └─ If already open: Switches to that tab

2. Work with report
   └─ View chart/table
   └─ Apply filters
   └─ Data updates in real-time

3. Open another report
   └─ Click another report
   └─ New tab appears
   └─ Both tabs remain open

4. Switch between tabs
   └─ Click tab button in tab bar
   └─ Or click report in sidebar
   └─ Active tab highlighted in blue

5. Close a tab
   └─ Click × on tab button
   └─ Tab closes (if not last one)
   └─ Can re-open anytime from sidebar
```

---

## API Endpoints

### New Endpoint

**GET `/api/config/<tab_id>`**

Returns configuration for a tab needed for auto-detect filters.

**Response:**
```json
{
  "name": "Cost by Funding Block",
  "description": "Total costs grouped by...",
  "sql": "SELECT block_funding, SUM(total_cost) ...",
  "chart": {"type": "bar", ...},
  "filters": []
}
```

### Existing Endpoints

**GET `/api/data/<tab_id>`** - Get tab data
**GET `/api/filter-options/<tab_id>/<column>`** - Get filter values

---

## Responsive Design

### Desktop (>1024px)
```
┌─────────────────────────────┐
│  Header                     │
├────────────────────────────┐
│ Sidebar │ Tab Bar         │
│ (280px) │ [Tab1] [Tab2]   │
│         │ Content Area    │
│         │                 │
└─────────────────────────────┘
```

### Tablet (768px-1024px)
```
┌─────────────────────────────┐
│  Header                     │
├────────────────────────────┐
│ Sidebar │ Content Area     │
│ (200px) │ [Tab1] [Tab2]   │
│         │                 │
└─────────────────────────────┘
```

### Mobile (<768px)
```
┌──────────────────────────┐
│  Header                  │
├──────────────────────────┤
│ [Report1] [Report2] ... │
├──────────────────────────┤
│ [Tab1] [Tab2]           │
├──────────────────────────┤
│ Content Area            │
│                         │
└──────────────────────────┘
```

---

## State Management

### Tab State
```javascript
openTabs Map:
{
  "funding_block_costs": { button, content, dataLoaded },
  "top_users": { button, content, dataLoaded },
  ...
}

activeTabId: "funding_block_costs" (currently viewing)
allReports: [...all available reports from sidebar...]
```

### Filter State
```javascript
// Stored in form inputs
<select name="block_funding">
  <option value="">All block_funding</option>
  <option>Engineering</option>
  <option>Product</option>
  ...
</select>

// Used in API calls
/api/data/cost_by_vp?block_funding=Engineering&state=CA
```

---

## Performance Considerations

### Optimizations
- **Lazy loading:** Filters only created when tab becomes active
- **Data caching:** Marked with `dataLoaded` flag to avoid reloading
- **Query reuse:** Filter changes re-use existing data if possible
- **SQL parsing:** Done once per tab in JavaScript

### Best Practices
- Keep number of open tabs reasonable (~5-10)
- Close unused tabs to free browser memory
- Use filters to reduce data volume
- Sidebar scrolls if many reports exist

---

## Browser Support

- ✅ Chrome/Edge (100+)
- ✅ Firefox (90+)
- ✅ Safari (14+)
- ✅ Mobile browsers (iOS Safari, Chrome Android)

**Requirements:**
- JavaScript enabled
- ES6+ support (const, Map, spread operator)
- Fetch API
- CSS Grid/Flexbox

---

## Troubleshooting

### Issue: Sidebar not appearing
**Solution:** Check CSS was loaded correctly
```
DevTools → Elements → Look for .sidebar class
DevTools → Console → Check for CSS errors
```

### Issue: Tabs not opening
**Solution:** Check JavaScript for errors
```
DevTools → Console → Look for JS errors
Check that /api/config/<tab_id> returns valid JSON
```

### Issue: Filters not showing
**Solution:** Check SQL parsing
```
DevTools → Network → Check /api/config response
Verify SQL has SELECT and FROM clauses
```

### Issue: Only one tab shows
**Solution:** Browser might be caching old HTML
```
Clear browser cache: Ctrl+Shift+Delete
Force reload: Ctrl+Shift+R
```

---

## Future Enhancements

Possible improvements for later versions:

1. **Tab persistence** - Save open tabs in localStorage
2. **Tab groups** - Group related reports together
3. **Quick filters** - Pin common filters to top
4. **Filter presets** - Save filter combinations
5. **Tab reordering** - Drag to reorder tabs
6. **Keyboard shortcuts** - Alt+# to switch tabs
7. **Advanced filters** - Range sliders, date pickers
8. **Visual indicators** - Show data update status per tab

---

## Summary

| Feature | Before | After |
|---------|--------|-------|
| **Report list** | Horizontal tabs | Sidebar + tabs |
| **Multiple reports** | Pre-rendered all | Open on demand |
| **Tab closure** | Not possible | Click × button |
| **Filters** | Manual config | Auto-detected from SQL |
| **Mobile** | Tabs wrap | Sidebar collapses |
| **Performance** | Load all data | Lazy load per tab |

---

## Implementation Checklist

✅ HTML template updated
✅ CSS styling added
✅ JavaScript tab management
✅ Auto-detect filters
✅ SQL parsing
✅ Backend endpoint
✅ Testing
✅ Documentation

**Status:** Ready for use! 🚀
