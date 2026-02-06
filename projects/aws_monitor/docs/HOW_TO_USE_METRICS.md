# How to Use Performance Metrics

## 🎯 Quick Answer

You're seeing resource names in blue because you need to **check the boxes** next to resources first!

---

## 📖 Step-by-Step Guide

### Step 1: Discover Resources

1. Go to **section 1** (Region Selection)
2. Select regions (e.g., us-east-1, us-west-2)
3. Go to **section 2** (Resource Type Selection)
4. Select types (e.g., EC2, RDS)
5. Click **"Discover Resources"**

**Result**: Resources appear in section 4

---

### Step 2: Select Resources ☑️

This is the step you're missing!

1. **Scroll to section 4** (Discovered Resources)
2. **Click the checkboxes** ☑️ next to resources you want to monitor
3. You'll see the resource selected

**Visual Example**:
```
Resources by Type

EC2 (15 instances)
┌─────────────────────────────────────────┐
│ ☑️  i-abc123  web-server-1    Running  │  ← CHECK THIS BOX
│ ☐  i-def456  web-server-2    Running  │
│ ☑️  i-ghi789  api-server      Running  │  ← CHECK THIS BOX
└─────────────────────────────────────────┘
```

**Tip**: You can select multiple resources at once!

---

### Step 3: Get Metrics

1. **Scroll down to section 5** (Performance Metrics)
2. The button will now show: **"📊 Get Metrics (2 selected)"**
3. Click **"Get Metrics"**

**Result**: Metrics appear below!

---

## 📊 What You'll See

After clicking "Get Metrics", you'll see:

```
Performance Metrics

┌─────────────────────────────────────────┐
│ i-abc123                                │
│                                         │
│ CPU Utilization    Network Out          │
│     45.2%              123.4 MB        │
│ 👆 Click for...    👆 Click for...     │
│                                         │
│ Network In         Disk Read            │
│     89.1 MB            45.2 MB         │
│ 👆 Click for...    👆 Click for...     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ i-ghi789                                │
│                                         │
│ CPU Utilization    Network Out          │
│     78.5%              234.5 MB        │
│ ...                                     │
└─────────────────────────────────────────┘
```

**Each metric box is clickable** for detailed stats (avg, max, min, current)!

---

## ❌ Common Mistakes

### Mistake 1: Not Selecting Resources

**Problem**: Click "Get Metrics" without checking boxes

**What happens**: You see a message saying "Select Resources First"

**Solution**: Go back up and check the boxes ☑️

---

### Mistake 2: Clicking Resource Names Instead of Checkboxes

**Problem**: Clicking the resource name (blue text) instead of checkbox

**What happens**: Opens resource details modal (not what you want)

**Solution**: Click the checkbox ☑️ on the far left of each row

---

### Mistake 3: Not Discovering Resources First

**Problem**: Trying to get metrics before discovering

**What happens**: "Get Metrics" button is disabled (grayed out)

**Solution**: Discover resources first (sections 1-3)

---

## 🎯 Complete Workflow

```
┌─────────────────────────────────────────┐
│ 1. Select Regions                       │
│    [✓] us-east-1  [✓] us-west-2        │
│                                         │
│ 2. Select Resource Types                │
│    [✓] EC2  [✓] RDS  [ ] S3            │
│                                         │
│ 3. Click "Discover Resources"           │
│    [Discover Resources]                 │
│                                         │
│         ↓                               │
│                                         │
│ 4. CHECK BOXES next to resources ☑️     │
│    [☑️] i-abc123  web-server-1         │
│    [☑️] i-def456  web-server-2         │
│                                         │
│         ↓                               │
│                                         │
│ 5. Click "Get Metrics"                  │
│    [📊 Get Metrics (2 selected)]       │
│                                         │
│         ↓                               │
│                                         │
│ 6. See Metrics Below!                   │
│    CPU: 45%  Network: 123MB            │
└─────────────────────────────────────────┘
```

---

## 💡 UI Improvements Added

### 1. Button Shows Selection Count

**Before**: 📊 Get Metrics  
**After**: 📊 Get Metrics (2 selected)

Now you can see how many resources are selected!

---

### 2. Helpful Tip in Section

**New instruction** at top of Performance Metrics section:
```
💡 Tip: Check the boxes ☑️ next to resources above, 
        then click "Get Metrics"
```

---

### 3. Better Empty State Message

**When clicking without selection**:
```
        ☑️
Select Resources First

Please check the boxes next to resources to get their metrics

How to get metrics:
1. Scroll up to the discovered resources
2. Check the boxes ☑️ next to resources you want to monitor
3. Come back here and click "Get Metrics"

💡 Tip: You can select multiple resources at once
```

---

## 🔍 Troubleshooting

### "I don't see any checkboxes"

**Problem**: Resources not discovered yet

**Solution**: 
1. Go to section 1 (Regions)
2. Select at least one region
3. Go to section 2 (Resource Types)
4. Select at least one type
5. Click "Discover Resources"

---

### "The Get Metrics button is grayed out"

**Problem**: Haven't discovered resources yet

**Solution**: Follow the steps above to discover first

---

### "I checked boxes but nothing happens"

**Problem**: Need to click "Get Metrics" button

**Solution**: After checking boxes, scroll down to section 5 and click the button

---

### "I see 'No datapoints' for a resource"

**Problem**: CloudWatch doesn't have recent data for that resource

**Possible reasons**:
- Resource was just created (needs a few minutes)
- Resource is stopped (no metrics when stopped)
- Resource doesn't have CloudWatch enabled

**Solution**: Try a longer time period (15 minutes or 1 hour)

---

## 📸 Visual Checklist

Before clicking "Get Metrics", make sure:

- [✓] You've discovered resources (section 3)
- [✓] You see resources listed in section 4
- [✓] You've checked the boxes ☑️ (not just clicked names)
- [✓] Button shows "(X selected)" where X > 0
- [✓] Button is NOT grayed out

If all checked → Click "Get Metrics" → See metrics!

---

## 🎓 Pro Tips

### Tip 1: Select All in a Type

Click the checkbox in the **header** of each resource type to select all resources of that type.

```
EC2 (15 instances)
[☑️] Status  Name  Type  ...    ← Click this to select all EC2
```

---

### Tip 2: Compare Multiple Resources

Select multiple resources to see their metrics side-by-side:

```
☑️ web-server-1 → CPU: 45%
☑️ web-server-2 → CPU: 52%
☑️ web-server-3 → CPU: 38%
```

Quickly spot which server has high CPU!

---

### Tip 3: Click Metric Boxes for Details

Each metric box is clickable:

```
┌──────────────────┐
│ CPU Utilization  │
│      45.2%       │  ← Click this box
│ 👆 Click for...  │
└──────────────────┘

Opens detailed stats:
- Current: 45.2%
- Average: 42.8%
- Maximum: 67.3%
- Minimum: 23.1%
```

---

## ✅ Quick Checklist

When you want metrics:

1. [ ] Discovered resources?
2. [ ] Checked boxes ☑️?
3. [ ] Button shows count?
4. [ ] Clicked "Get Metrics"?
5. [ ] See metrics below?

If you answered "yes" to all → You're done! 🎉

---

## 🎉 Summary

**The key thing**: You must **CHECK THE BOXES** ☑️ next to resources

**Not**: Just look at them  
**Not**: Click their names  
**But**: Click the checkboxes on the left

**Then**: Scroll down and click "Get Metrics"

**Result**: Beautiful metric displays with CPU, Network, Disk data!

---

## 📞 Still Stuck?

If you still see only blue text:

1. **Refresh the page** and try again
2. **Check browser console** for errors (F12 → Console)
3. **Try with one resource** first (easier to debug)
4. **Check the section 4** - are resources actually discovered?

---

**Happy monitoring!** 📊🎉
