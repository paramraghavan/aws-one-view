# Lambda Performance Metrics Guide

## 🎯 Quick Answer

Lambda metrics only appear **when the function has been invoked**. If you see a yellow box saying "No recent invocations", your Lambda function hasn't been called during the selected time period.

---

## 📊 Lambda Metrics Available

When a Lambda function is active, you'll see these metrics:

### 1. **Invocations**
- **What**: Number of times the function was called
- **Shows**: Total count in the time period
- **Example**: 150 invocations in the last hour

### 2. **Errors**
- **What**: Number of invocations that resulted in errors
- **Shows**: Total error count
- **Example**: 3 errors (2% error rate)

### 3. **Duration**
- **What**: How long the function took to execute
- **Shows**: Average, Max, Min execution time
- **Units**: Milliseconds (ms)
- **Example**: Avg: 245ms, Max: 890ms

### 4. **Throttles**
- **What**: Number of invocations that were throttled (rate limited)
- **Shows**: Total throttle count
- **Example**: 0 throttles (good!)

---

## ⚠️ Why Don't I See Metrics?

### Reason 1: No Recent Invocations

**Problem**: Lambda function hasn't been called recently

**You see**:
```
⏱️
No recent invocations - Lambda metrics only 
appear when function is called

Try: Invoke the function or select "1 hour" period
```

**Solution**:
1. Invoke the function manually in AWS Console
2. Wait for scheduled triggers to run
3. Select a longer time period (1 hour instead of 5 minutes)
4. Check if the function is actually being used

---

### Reason 2: Time Period Too Short

**Problem**: Selected 5 minutes, but function only runs hourly

**Example**:
- Function runs every hour at :00
- Current time: 2:30 PM
- Last invocation: 2:00 PM (30 minutes ago)
- Selected period: 5 minutes
- Result: No data in last 5 minutes

**Solution**: Select "1 hour" period

---

### Reason 3: Function Is Dormant

**Problem**: Function exists but is not being used

**Scenarios**:
- Development/test function no longer in use
- Disabled event trigger (e.g., S3 event not firing)
- Scheduled CloudWatch Events disabled
- API Gateway route removed

**Solution**: 
- Check if function should be running
- Verify triggers in AWS Console
- Consider deleting if no longer needed

---

## 🔧 How to Get Lambda Metrics

### Step 1: Make Sure Function Has Run

**Test invoke the function**:

```bash
# Using AWS CLI
aws lambda invoke \
  --function-name my-function \
  --payload '{"test": true}' \
  response.json
```

**Or in AWS Console**:
1. Go to Lambda → Functions
2. Click your function
3. Click "Test" tab
4. Create test event
5. Click "Test" button

---

### Step 2: Wait a Few Minutes

CloudWatch metrics have a slight delay:
- **Invocations**: 1-2 minutes
- **Duration**: 1-2 minutes  
- **Errors**: 1-2 minutes

**Don't check immediately** - wait 2-3 minutes after invocation

---

### Step 3: Select Appropriate Time Period

**If function runs**:
- Every minute → Use "5 minutes"
- Every 15 minutes → Use "15 minutes"
- Every hour → Use "1 hour"
- Occasionally → Use "1 hour"

**In AWS Monitor**:
```
Performance Metrics

Period: [1 hour ▼]  ← Select here
```

---

### Step 4: Check Metrics

After invocation and waiting:

```
Performance Metrics

┌────────────────────────────────────┐
│ lambda:my-function                 │
├────────────────────────────────────┤
│                                    │
│  Invocations        Errors         │
│      5                 0            │
│  👆 Click for... 👆 Click for...   │
│                                    │
│  Duration           Throttles      │
│     245.32 ms          0           │
│  👆 Click for... 👆 Click for...   │
│                                    │
└────────────────────────────────────┘
```

---

## 📈 Understanding Lambda Metrics

### Invocations

**What you see**: `5` invocations

**Details** (click the box):
- Current: 5 (last data point)
- Total: 5 (sum across period)
- Average: 1.25 per interval
- Max: 3 (peak invocations in one interval)

**Good**: Any number > 0 (function is working)
**Bad**: 0 (function not being called)

---

### Errors

**What you see**: `2` errors

**Details** (click the box):
- Current: 0 (last invocation succeeded)
- Total: 2 (total errors in period)
- Average: 0.5 per interval
- Max: 2 (worst interval)

**Good**: 0 errors
**Warning**: 1-5% error rate (investigate)
**Bad**: >5% error rate (urgent fix needed)

**Calculate error rate**:
```
Error Rate = (Errors / Invocations) × 100
Example: (2 / 50) × 100 = 4%
```

---

### Duration

**What you see**: `245.32 ms`

**Details** (click the box):
- Current: 234.21 ms (last invocation)
- Average: 245.32 ms (typical)
- Maximum: 890.45 ms (slowest)
- Minimum: 123.67 ms (fastest)

**What's good**:
- Function < 1000 ms (1 second): ✅ Excellent
- Function < 3000 ms (3 seconds): ✅ Good
- Function < 10000 ms (10 seconds): ⚠️ Slow
- Function > 10000 ms: ❌ Very slow

**Why duration matters**:
- Faster = cheaper (Lambda charges per ms)
- Faster = better user experience
- Consistent = predictable performance

---

### Throttles

**What you see**: `0` throttles

**Details** (click the box):
- Current: 0 (last invocation not throttled)
- Total: 0 (no throttles in period)
- Average: 0 per interval
- Max: 0

**Good**: 0 throttles (you have enough concurrency)
**Bad**: >0 throttles (hitting concurrency limits)

**What throttling means**:
- Lambda has concurrency limits (default: 1000 concurrent executions)
- When limit reached, new invocations are rejected
- Results in errors for your application

**Fix throttling**:
1. Request concurrency increase from AWS
2. Optimize function to run faster
3. Reduce invocation rate

---

## 🎯 Real-World Examples

### Example 1: Healthy Function

```
lambda:process-orders

Invocations: 150
Errors: 0
Duration: 234.56 ms
Throttles: 0
```

**Analysis**: ✅ Perfect!
- Function is being used (150 invocations)
- No errors (100% success rate)
- Fast execution (< 1 second)
- No throttling issues

---

### Example 2: Slow Function

```
lambda:generate-report

Invocations: 25
Errors: 0
Duration: 8,234.12 ms
Throttles: 0
```

**Analysis**: ⚠️ Needs optimization
- Function works (no errors)
- Very slow (8+ seconds)
- Costing more money than necessary
- Users waiting too long

**Action**: Optimize the function code

---

### Example 3: Error-Prone Function

```
lambda:api-handler

Invocations: 100
Errors: 15
Duration: 456.78 ms
Throttles: 0
```

**Analysis**: ❌ Has issues
- 15% error rate (too high!)
- Duration is fine
- Need to investigate errors

**Action**: Check CloudWatch Logs for error details

---

### Example 4: Throttled Function

```
lambda:batch-processor

Invocations: 500
Errors: 50
Duration: 123.45 ms
Throttles: 50
```

**Analysis**: ❌ Hitting limits
- High invocation rate
- 10% throttle rate
- Errors likely due to throttling
- Need more concurrency

**Action**: Request concurrency increase

---

### Example 5: Unused Function

```
⏱️
No recent invocations - Lambda metrics only 
appear when function is called
```

**Analysis**: ⚠️ Not being used
- Function exists but dormant
- No triggers firing
- Might be obsolete

**Action**: Check if function is still needed

---

## 💡 Pro Tips

### Tip 1: Compare Before/After Changes

**Before deployment**:
```
Duration: 500 ms
Errors: 0
```

**After optimization**:
```
Duration: 200 ms  ← 60% faster!
Errors: 0
```

**Result**: $300/month cost savings!

---

### Tip 2: Monitor Error Rate

**Set alerts** when error rate > 5%:
```
Error Rate = (Errors / Invocations) × 100

If > 5% → Investigate immediately
```

---

### Tip 3: Track Duration Trends

**Watch for increasing duration**:
```
Week 1: 200 ms
Week 2: 250 ms
Week 3: 300 ms  ← Trending up!
```

**Could indicate**:
- Memory leak
- Database getting slower
- Need to scale dependencies

---

### Tip 4: Check Throttles Daily

**Even 1 throttle** indicates:
- Approaching concurrency limits
- Need to plan for scaling
- Might impact users soon

---

## 🔍 Troubleshooting

### "I invoked the function but still see no metrics"

**Checklist**:
- [ ] Waited 2-3 minutes?
- [ ] Selected "1 hour" period?
- [ ] Function actually executed (check CloudWatch Logs)?
- [ ] Selected correct region?
- [ ] Clicked "Refresh" in AWS Monitor?

---

### "Metrics show but values are 0"

**Possible causes**:
1. Function invocations failed before completion
2. Time period doesn't include invocations
3. Viewing wrong function (check function name)

**Solution**: 
- Check CloudWatch Logs for errors
- Verify function name is correct
- Select longer time period

---

### "Duration seems wrong"

**Remember**:
- Duration includes **cold starts** (first invocation slower)
- Average duration smooths out spikes
- Max duration shows worst-case

**Example**:
```
Invocations: 10
Duration (avg): 245 ms

Breakdown:
- 9 invocations: ~200 ms (warm)
- 1 invocation: 650 ms (cold start)
- Average: 245 ms
```

---

## 📚 Additional Resources

### AWS Console
Check detailed metrics:
1. Go to Lambda → Functions → Your Function
2. Click "Monitor" tab
3. See graphs and detailed metrics

### CloudWatch Logs
See actual errors:
1. Go to CloudWatch → Logs
2. Find `/aws/lambda/your-function`
3. View error messages

### X-Ray Tracing
See detailed performance:
1. Enable X-Ray in Lambda settings
2. View execution breakdown
3. Identify slow components

---

## ✅ Quick Checklist

To see Lambda metrics:

- [ ] Function has been invoked recently
- [ ] Waited 2-3 minutes after invocation
- [ ] Selected appropriate time period
- [ ] Checked the boxes ☑️ in resource list
- [ ] Clicked "Get Metrics"

If all checked → Should see metrics!

If not → Function might not be active

---

## 🎉 Summary

**Key Points**:

1. **Lambda metrics only appear when function is invoked**
2. **Select appropriate time period** based on function schedule
3. **Wait 2-3 minutes** after invocation for metrics to appear
4. **Four metrics**: Invocations, Errors, Duration, Throttles
5. **Click metric boxes** for detailed statistics

**Common Issue**: Seeing yellow "No recent invocations" box means function hasn't run

**Solution**: Invoke function or select longer time period

---

**Now you know why Lambda metrics might not appear!** 📊🎉
