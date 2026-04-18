# D3.js Examples

Complete, working examples of D3.js charts that you can open directly in your browser and learn from!

---

## Quick Start

1. Open any HTML file in your browser
2. No server needed - they work offline!
3. Inspect the source code to see how D3.js works
4. Modify and experiment

---

## Examples Included

### 1. **01_simple_bar_chart.html** - Basic Bar Chart

**Concepts:**
- Creating SVG elements
- Scales (scaleBand, scaleLinear)
- Axes (axisBottom, axisLeft)
- Bar rendering
- Click interactions

**Data:** Cost by department

**Features:**
- Click bars to see values
- Hover highlighting
- Value labels on bars

**Key code:**
```javascript
const xScale = d3.scaleBand()
    .domain(data.map(d => d.department))
    .range([0, width]);

svg.selectAll(".bar")
    .data(data)
    .append("rect")
    .attr("x", d => xScale(d.department));
```

---

### 2. **02_pie_chart.html** - Pie Chart

**Concepts:**
- Pie generator (d3.pie)
- Arc generator (d3.arc)
- Color scales
- Percentage calculations
- Legend rendering

**Data:** Funding block distribution

**Features:**
- Hover to highlight
- Click for percentage popup
- Color legend below chart
- Percentage labels on slices

**Key code:**
```javascript
const pie = d3.pie().value(d => d.value);
const arc = d3.arc().outerRadius(radius);

svg.selectAll(".arc")
    .data(pie(data))
    .append("path")
    .attr("d", arc)
    .attr("fill", (d, i) => colorScale(i));
```

---

### 3. **03_line_chart.html** - Line Chart with Trend

**Concepts:**
- Line generator (d3.line)
- Linear scales
- Grid lines
- Tooltip positioning
- Trend analysis

**Data:** Weekly cost trend (12 weeks)

**Features:**
- Hover dots for tooltip
- Grid background
- Trend annotation
- Smooth line paths

**Key code:**
```javascript
const line = d3.line()
    .x(d => xScale(d.week))
    .y(d => yScale(d.cost));

svg.append("path")
    .datum(data)
    .attr("d", line);
```

---

### 4. **04_interactive_chart.html** - Interactive with Sliders

**Concepts:**
- Real-time updates
- Transitions
- Event listeners
- Dynamic calculations
- Live statistics

**Data:** Department costs (editable with sliders)

**Features:**
- 3 sliders to adjust values
- Chart updates in real-time
- Live statistics (Total, Avg, Max)
- Reset button
- Visual feedback

**Key code:**
```javascript
document.getElementById("slider").addEventListener("input", function() {
    data[0].cost = this.value;
    initChart();  // Redraw
});

// Transitions
svg.selectAll(".bar")
    .transition()
    .duration(500)
    .attr("height", d => height - yScale(d.cost));
```

---

### 5. **05_horizontal_bar_chart.html** - Horizontal Bars with Sorting

**Concepts:**
- Horizontal orientation
- Dynamic sorting
- Animated transitions
- Data transformation
- State management

**Data:** Top 8 users by cost

**Features:**
- Sort by cost or name
- Animated bar transitions
- Animated axis labels
- Value labels after animation
- Button state management

**Key code:**
```javascript
const yScale = d3.scaleBand()
    .domain(sortedData.map(d => d.name))
    .range([0, height]);

svg.selectAll(".bar")
    .transition()
    .duration(500)
    .attr("width", d => xScale(d.cost));
```

---

## Learning Path

### Beginner
Start with these to understand basics:
1. **01_simple_bar_chart.html** - Learn SVG, scales, axes
2. **02_pie_chart.html** - Learn generators (pie, arc)
3. **03_line_chart.html** - Learn line paths and tooltips

### Intermediate
Build on basics:
4. **04_interactive_chart.html** - Learn updates and transitions
5. **05_horizontal_bar_chart.html** - Learn sorting and state

### Advanced
Combine concepts:
- Add filters to bar charts
- Combine multiple chart types
- Add zoom/pan interactions
- Implement legends and tooltips

---

## Common Patterns

### Pattern 1: Create Scales
```javascript
// Categorical scale (for categories)
const xScale = d3.scaleBand()
    .domain(data.map(d => d.name))
    .range([0, width])
    .padding(0.2);

// Linear scale (for numbers)
const yScale = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.value)])
    .range([height, 0]);
```

### Pattern 2: Bind Data
```javascript
svg.selectAll(".bar")
    .data(data)
    .enter()
    .append("rect")
    .attr("x", d => xScale(d.name))
    .attr("y", d => yScale(d.value));
```

### Pattern 3: Add Axes
```javascript
// X axis
svg.append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale));

// Y axis
svg.append("g")
    .call(d3.axisLeft(yScale));
```

### Pattern 4: Add Interactions
```javascript
.on("click", function(event, d) {
    alert(`${d.name}: ${d.value}`);
})
.on("mouseover", function() {
    d3.select(this).style("opacity", 1);
})
.on("mouseout", function() {
    d3.select(this).style("opacity", 0.8);
});
```

### Pattern 5: Transitions
```javascript
svg.selectAll(".bar")
    .transition()
    .duration(500)  // 500ms animation
    .attr("x", newX)
    .attr("y", newY)
    .attr("height", newHeight);
```

---

## Modifications to Try

### Easy
1. Change colors in any chart
2. Modify sample data
3. Change chart title
4. Adjust margins and dimensions

### Medium
1. Add more data points
2. Create your own dataset
3. Combine charts (bar + line)
4. Add multiple categories

### Hard
1. Implement zooming
2. Add filtering controls
3. Create animations on load
4. Multi-series comparison

---

## Key D3.js Concepts

| Concept | What | When |
|---------|------|------|
| **Selections** | Choose elements | `d3.select("#id")` |
| **Data Binding** | Link data to elements | `.data(array)` |
| **Scales** | Map data to pixels | `scaleLinear()`, `scaleBand()` |
| **Axes** | Draw axis lines | `axisBottom()`, `axisLeft()` |
| **Generators** | Create shapes | `line()`, `pie()`, `arc()` |
| **Transitions** | Animate changes | `.transition().duration(500)` |
| **Events** | Handle interactions | `.on("click", fn)` |

---

## Debugging Tips

### Check if element exists
```javascript
console.log(d3.select("#chart").node());
```

### Log data binding
```javascript
.data(data)
.each(function(d) { console.log(d); })
```

### Check scales
```javascript
console.log(xScale(data[0].name));  // Should be pixel position
```

### View source code
- Open browser DevTools (F12)
- Go to Elements tab
- Inspect the SVG structure

---

## Resources

- **D3.js Official**: https://d3js.org
- **Observable Notebooks**: https://observablehq.com/@d3 (interactive examples)
- **D3.js API**: https://github.com/d3/d3/wiki/API-Reference
- **D3.js Gallery**: https://github.com/d3/d3/wiki/Gallery

---

## Common Errors & Fixes

### Error: "x is not a function"
```javascript
// Wrong
d3.select("chart").append("svg");

// Right
d3.select("#chart").append("svg");
```

### Error: "Cannot read property 'value'"
```javascript
// Make sure data has the property
console.log(data[0]);  // Check what properties exist
```

### Chart not showing
```javascript
// Check SVG size
.attr("width", 800)
.attr("height", 400)

// Check if appended to right element
d3.select("#chart").append("svg");  // Make sure #chart exists in HTML
```

### Bars all same size
```javascript
// Make sure scale domain includes 0
.domain([0, d3.max(data, d => d.value)])  // Includes 0
// Not
.domain([d3.min(...), d3.max(...)])  // Wrong!
```

---

## Practice Exercises

1. **Modify 01**: Change from departments to regions
2. **Modify 02**: Add a second pie chart for comparison
3. **Modify 03**: Make the line chart for 2 different users
4. **Modify 04**: Add 4th slider instead of 3
5. **Modify 05**: Add reverse sort button

---

## Next Steps

After mastering these examples:
1. Try examples from [Observable Notebooks](https://observablehq.com/@d3)
2. Read the [D3.js docs](https://github.com/d3/d3/wiki)
3. Implement charts in your own projects
4. Build dashboards combining multiple visualizations

---

## File Overview

```
examples/
├── README.md                          ← You are here
├── 01_simple_bar_chart.html          ← Start here
├── 02_pie_chart.html
├── 03_line_chart.html
├── 04_interactive_chart.html
└── 05_horizontal_bar_chart.html
```

**Pro tip:** Open these in your editor side-by-side with a browser to see changes in real-time!

Happy learning! 🎨📊
