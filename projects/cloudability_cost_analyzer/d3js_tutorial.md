# D3.js Tutorial - Pie Charts & Histograms

A beginner-friendly guide to understanding D3.js visualizations used in the Reporting Engine.

---

## Table of Contents
1. [D3.js Basics](#basics)
2. [Pie Chart Example](#pie-chart)
3. [Bar Chart (Histogram) Example](#bar-chart)
4. [How Our Charts Work](#how-our-charts-work)
5. [Customization Guide](#customization-guide)

---

## Basics

### What is D3.js?

D3 (Data-Driven Documents) binds data to DOM elements and applies data-driven transformations.

```
Data → Select Elements → Bind Data → Apply Attributes → Render
```

### Basic Pattern

```javascript
// 1. Select a container
const svg = d3.select('#container');

// 2. Bind data to elements
svg.selectAll('rect')
   .data(myData)
   .enter()
   .append('rect')
   .attr('x', d => d.x)
   .attr('y', d => d.y)
   .attr('width', d => d.width);
```

### Scales (Mapping data to visual properties)

```javascript
// Linear scale: convert numbers to pixel positions
const xScale = d3.scaleLinear()
    .domain([0, 100])        // Input: 0-100
    .range([0, 800]);        // Output: 0-800 pixels

xScale(50);  // Returns 400 (middle of range)

// Band scale: map categories to positions
const yScale = d3.scaleBand()
    .domain(['A', 'B', 'C'])  // Categories
    .range([0, 300]);         // Width in pixels
    .padding(0.2);            // 20% padding

yScale('A');  // Returns 0
yScale('B');  // Returns 100
```

---

## Pie Chart Example

### Data Format
```javascript
const data = [
    { label: "Engineering", value: 45000 },
    { label: "Product", value: 30000 },
    { label: "Research", value: 25000 }
];
```

### Basic Pie Chart

```javascript
function createPieChart() {
    // 1. Set dimensions
    const width = 400;
    const height = 400;
    const radius = Math.min(width, height) / 2 - 40;

    // 2. Create SVG
    const svg = d3.select('#chart')
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', `translate(${width / 2},${height / 2})`);

    // 3. Create pie generator
    const pie = d3.pie()
        .value(d => d.value);  // Use 'value' field for slice size

    // 4. Create arc generator
    const arc = d3.arc()
        .innerRadius(0)        // 0 for full pie, >0 for donut
        .outerRadius(radius);

    // 5. Create color scale
    const colors = d3.scaleOrdinal(d3.schemeCategory10);

    // 6. Bind data and create slices
    svg.selectAll('.arc')
        .data(pie(data))
        .enter()
        .append('g')
        .attr('class', 'arc')
        .append('path')
        .attr('d', arc)
        .attr('fill', (d, i) => colors(i));

    // 7. Add labels
    svg.selectAll('.arc')
        .data(pie(data))
        .enter()
        .append('text')
        .attr('transform', d => `translate(${arc.centroid(d)})`)
        .attr('text-anchor', 'middle')
        .text(d => d.data.label);
}
```

### Step-by-Step Breakdown

#### Step 1: Define Data
```javascript
const data = [
    { label: "A", value: 30 },
    { label: "B", value: 20 },
    { label: "C", value: 50 }
];
```

#### Step 2: Create SVG Container
```javascript
const svg = d3.select('#container')  // Select HTML element
    .append('svg')                   // Add SVG
    .attr('width', 400)
    .attr('height', 400)
    .append('g')                     // Add group for translation
    .attr('transform', 'translate(200, 200)');  // Center the group
```

#### Step 3: Pie Generator
```javascript
const pie = d3.pie().value(d => d.value);

// Converts data to angles for pie slices
// Input: [{ label: "A", value: 30 }]
// Output: [{ data: {...}, startAngle: 0, endAngle: 1.88... }]
```

#### Step 4: Arc Generator
```javascript
const arc = d3.arc()
    .innerRadius(0)           // 0 = pie, 50 = donut
    .outerRadius(150);

// Converts angles to SVG path commands
// Input: { startAngle: 0, endAngle: 1.88 }
// Output: "M 0,-150 A 150,150 0 0,1 106,106 L 0,0 Z"
```

#### Step 5: Bind Data & Create Elements
```javascript
svg.selectAll('.arc')           // Select all (initially empty)
    .data(pie(data))            // Bind data
    .enter()                    // Create placeholder for new data
    .append('g')                // Add group for each slice
    .attr('class', 'arc')
    .append('path')             // Add path element
    .attr('d', arc)             // Set path using arc generator
    .attr('fill', (d, i) => colors(i));  // Color each slice
```

#### Step 6: Add Labels
```javascript
svg.selectAll('text')
    .data(pie(data))
    .enter()
    .append('text')
    .attr('transform', d => `translate(${arc.centroid(d)})`)  // Position at center
    .text(d => `${d.data.label}: ${d.data.value}`);
```

### Complete Working Example

```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        .arc path { stroke: white; stroke-width: 2; }
        .arc text { font-size: 12px; font-weight: bold; fill: white; }
    </style>
</head>
<body>
    <div id="chart"></div>

    <script>
        const data = [
            { label: "Engineering", value: 45 },
            { label: "Product", value: 30 },
            { label: "Research", value: 25 }
        ];

        const width = 500, height = 500;
        const radius = Math.min(width, height) / 2 - 40;

        const svg = d3.select('#chart')
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .append('g')
            .attr('transform', `translate(${width/2},${height/2})`);

        const pie = d3.pie().value(d => d.value);
        const arc = d3.arc().innerRadius(0).outerRadius(radius);
        const colors = d3.scaleOrdinal(d3.schemeCategory10);

        const slices = svg.selectAll('.arc')
            .data(pie(data))
            .enter()
            .append('g')
            .attr('class', 'arc');

        slices.append('path')
            .attr('d', arc)
            .attr('fill', (d, i) => colors(i));

        slices.append('text')
            .attr('transform', d => `translate(${arc.centroid(d)})`)
            .attr('text-anchor', 'middle')
            .text(d => d.data.label);
    </script>
</body>
</html>
```

---

## Bar Chart (Histogram) Example

### Data Format
```javascript
const data = [
    { category: "Engineering", cost: 45000 },
    { category: "Product", cost: 30000 },
    { category: "Research", cost: 25000 },
    { category: "Operations", cost: 15000 }
];
```

### Basic Bar Chart

```javascript
function createBarChart() {
    // 1. Set dimensions
    const margin = { top: 20, right: 30, bottom: 60, left: 70 };
    const width = 800 - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    // 2. Create SVG
    const svg = d3.select('#chart')
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // 3. Create scales
    const xScale = d3.scaleBand()
        .domain(data.map(d => d.category))
        .range([0, width])
        .padding(0.2);

    const yScale = d3.scaleLinear()
        .domain([0, d3.max(data, d => d.cost)])
        .range([height, 0]);

    // 4. Create bars
    svg.selectAll('.bar')
        .data(data)
        .enter()
        .append('rect')
        .attr('class', 'bar')
        .attr('x', d => xScale(d.category))
        .attr('y', d => yScale(d.cost))
        .attr('width', xScale.bandwidth())
        .attr('height', d => height - yScale(d.cost));

    // 5. Add X axis
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(xScale));

    // 6. Add Y axis
    svg.append('g')
        .call(d3.axisLeft(yScale));
}
```

### Step-by-Step Breakdown

#### Step 1: Define Data
```javascript
const data = [
    { category: "Q1", sales: 30000 },
    { category: "Q2", sales: 45000 },
    { category: "Q3", sales: 35000 },
    { category: "Q4", sales: 50000 }
];
```

#### Step 2: Create SVG with Margins
```javascript
const margin = { top: 20, right: 30, bottom: 60, left: 70 };
const width = 800 - margin.left - margin.right;    // 700px actual width
const height = 400 - margin.top - margin.bottom;   // 320px actual height

const svg = d3.select('#container')
    .append('svg')
    .attr('width', width + margin.left + margin.right)    // 800px total
    .attr('height', height + margin.top + margin.bottom)  // 400px total
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);
    // Move group 70px right, 20px down
```

#### Step 3: Create Scales

**X Scale (Categories)**
```javascript
const xScale = d3.scaleBand()
    .domain(['Q1', 'Q2', 'Q3', 'Q4'])    // Categories
    .range([0, 700])                     // Width in pixels
    .padding(0.2);                       // 20% gap between bars

xScale('Q1');        // Returns 0 (start of Q1 bar)
xScale.bandwidth();  // Returns ~160 (bar width)
```

**Y Scale (Values)**
```javascript
const yScale = d3.scaleLinear()
    .domain([0, 50000])      // Min to max value
    .range([320, 0]);        // Pixels (flipped: top=0, bottom=320)

yScale(0);       // Returns 320 (bottom)
yScale(50000);   // Returns 0 (top)
yScale(25000);   // Returns 160 (middle)
```

#### Step 4: Create Bars
```javascript
svg.selectAll('rect')      // Select all rect (initially none)
    .data(data)            // Bind data
    .enter()               // Prepare to add new elements
    .append('rect')        // Add rect for each data point
    .attr('x', d => xScale(d.category))           // Position left
    .attr('y', d => yScale(d.sales))              // Position top
    .attr('width', xScale.bandwidth())            // Bar width
    .attr('height', d => height - yScale(d.sales));  // Bar height
```

#### Step 5: Add Axes
```javascript
// X Axis
svg.append('g')
    .attr('transform', `translate(0,${height})`)  // Move to bottom
    .call(d3.axisBottom(xScale));                 // Draw axis

// Y Axis
svg.append('g')
    .call(d3.axisLeft(yScale));                   // Draw axis
```

### Complete Working Example

```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        .bar { fill: #87CEEB; }
        .bar:hover { fill: #1E90FF; }
        .axis { font-size: 12px; }
        .axis line, .axis path { stroke: #ddd; }
    </style>
</head>
<body>
    <div id="chart"></div>

    <script>
        const data = [
            { category: "Engineering", cost: 45 },
            { category: "Product", cost: 30 },
            { category: "Research", cost: 25 },
            { category: "Operations", cost: 15 }
        ];

        const margin = { top: 20, right: 30, bottom: 60, left: 70 };
        const width = 800 - margin.left - margin.right;
        const height = 400 - margin.top - margin.bottom;

        const svg = d3.select('#chart')
            .append('svg')
            .attr('width', width + margin.left + margin.right)
            .attr('height', height + margin.top + margin.bottom)
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        const xScale = d3.scaleBand()
            .domain(data.map(d => d.category))
            .range([0, width])
            .padding(0.2);

        const yScale = d3.scaleLinear()
            .domain([0, d3.max(data, d => d.cost)])
            .range([height, 0]);

        svg.selectAll('.bar')
            .data(data)
            .enter()
            .append('rect')
            .attr('class', 'bar')
            .attr('x', d => xScale(d.category))
            .attr('y', d => yScale(d.cost))
            .attr('width', xScale.bandwidth())
            .attr('height', d => height - yScale(d.cost));

        svg.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(xScale));

        svg.append('g')
            .call(d3.axisLeft(yScale));
    </script>
</body>
</html>
```

---

## How Our Charts Work

### In the Reporting Engine

**Pie Chart Code** (dashboard.js lines 283-370)
```javascript
function renderPieChart(container, data) {
    const config = data.chart_config;
    const xAxis = config.x_axis;      // Category column
    const yAxis = config.y_axis;      // Value column

    const pie = d3.pie().value(d => d[yAxis]);
    const arc = d3.arc().innerRadius(0).outerRadius(radius);
    const colors = d3.scaleOrdinal(skyBlueColors);

    svg.selectAll('.arc')
        .data(pie(data.data))
        .enter()
        .append('path')
        .attr('d', arc)
        .attr('fill', (d, i) => colors(i));
}
```

**Bar Chart Code** (dashboard.js lines 121-280)
```javascript
function renderBarChart(container, data) {
    const xScale = d3.scaleBand()
        .domain(data.data.map(d => d[xAxis]))
        .range([0, width])
        .padding(0.2);

    const yScale = d3.scaleLinear()
        .domain([0, d3.max(data.data, d => d[yAxis])])
        .range([height, 0]);

    svg.selectAll('.bar')
        .data(data.data)
        .enter()
        .append('rect')
        .attr('x', d => xScale(d[xAxis]))
        .attr('y', d => yScale(d[yAxis]))
        .attr('width', xScale.bandwidth())
        .attr('height', d => height - yScale(d[yAxis]));
}
```

---

## Customization Guide

### Change Bar Colors

In `static/css/style.css`:
```css
.bar {
    fill: #87CEEB;      /* Change this color */
    opacity: 0.8;
}

.bar:hover {
    fill: #1E90FF;      /* Hover color */
    opacity: 1;
}
```

### Add Values on Bars

In `dashboard.js` renderBarChart():
```javascript
svg.selectAll('.bar-value')
    .data(data.data)
    .enter()
    .append('text')
    .attr('x', d => xScale(d[xAxis]) + xScale.bandwidth() / 2)
    .attr('y', d => yScale(d[yAxis]) - 5)
    .attr('text-anchor', 'middle')
    .text(d => formatValue(d[yAxis], data.format_config));
```

### Change Pie Chart to Donut

In `dashboard.js` renderPieChart():
```javascript
const arc = d3.arc()
    .innerRadius(50)        // Change from 0 to 50 for donut hole
    .outerRadius(radius);
```

### Add Tooltip on Hover

```javascript
.on('mouseover', function (event, d) {
    d3.select(this).style('opacity', 1);
    showTooltip(event, `Value: ${d.value}`);
})
.on('mouseout', function () {
    d3.select(this).style('opacity', 0.8);
    hideTooltip();
});
```

### Sort Bars

```javascript
// Sort by value descending
data.sort((a, b) => b.cost - a.cost);

// Or in SQL query:
// ORDER BY cost DESC
```

### Add Animation

```javascript
svg.selectAll('.bar')
    .data(data)
    .enter()
    .append('rect')
    .attr('height', 0)  // Start at 0
    .attr('y', height)  // Start at bottom
    .transition()       // Add transition
    .duration(500)      // 500ms animation
    .attr('height', d => height - yScale(d.cost))
    .attr('y', d => yScale(d.cost));
```

---

## Common Patterns

### Update Chart with New Data
```javascript
const update = svg.selectAll('.bar').data(newData);

// Remove old bars
update.exit().remove();

// Update existing bars
update
    .attr('x', d => xScale(d.category))
    .attr('y', d => yScale(d.cost))
    .attr('height', d => height - yScale(d.cost));

// Add new bars
update.enter()
    .append('rect')
    .attr('class', 'bar')
    .attr('x', d => xScale(d.category))
    .attr('y', d => yScale(d.cost))
    .attr('width', xScale.bandwidth())
    .attr('height', d => height - yScale(d.cost));
```

### Format Numbers
```javascript
function formatValue(value, config) {
    if (config.currency) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(value);
    }
    return value.toFixed(config.decimal_places || 0);
}
```

---

## Resources

- **D3.js Official**: https://d3js.org
- **D3.js Docs**: https://github.com/d3/d3/wiki
- **Observable**: https://observablehq.com/@d3 (Interactive examples)
- **API Reference**: https://d3js.org/api

---

## Summary

| Concept | Use Case |
|---------|----------|
| `d3.pie()` | Convert values to angles for pie slices |
| `d3.arc()` | Convert angles to SVG paths |
| `d3.scaleBand()` | Map categories to positions |
| `d3.scaleLinear()` | Map numbers to pixel positions |
| `.data()` | Bind data to elements |
| `.enter()` | Create elements for new data |
| `.attr()` | Set element attributes |
| `.transition()` | Animate changes |

You now understand how the charts in the Reporting Engine work! Try modifying the examples above to experiment with D3.js. 🎨📊
