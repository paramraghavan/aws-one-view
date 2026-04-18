// Dashboard Tab Management

const openTabs = new Map(); // tab_id → {button, content}
let activeTabId = null;
const allReports = [];

document.addEventListener('DOMContentLoaded', function() {
    initDashboard();
});

function initDashboard() {
    // Collect all reports from sidebar
    document.querySelectorAll('.sidebar-item').forEach(item => {
        const tabId = item.getAttribute('data-tab-id');
        const tabName = item.querySelector('.tab-label').textContent;
        allReports.push({id: tabId, name: tabName});
    });

    // Setup sidebar click handlers
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.addEventListener('click', function() {
            openTab(this.getAttribute('data-tab-id'));
        });
    });

    // Open first report by default
    if (allReports.length > 0) {
        openTab(allReports[0].id);
    }
}

function openTab(tabId) {
    // If already open, just switch to it
    if (openTabs.has(tabId)) {
        switchTab(tabId);
        return;
    }

    // Create new tab
    createTab(tabId);
    switchTab(tabId);
    loadTabData(tabId);
}

function createTab(tabId) {
    const report = allReports.find(r => r.id === tabId);
    const reportName = report ? report.name : tabId;

    // Create tab button
    const tabButton = document.createElement('button');
    tabButton.className = 'tab-button';
    tabButton.setAttribute('data-tab-id', tabId);
    tabButton.innerHTML = `
        <span class="tab-name">${reportName}</span>
        <span class="tab-close">×</span>
    `;

    // Close button click handler
    tabButton.querySelector('.tab-close').addEventListener('click', (e) => {
        e.stopPropagation();
        closeTab(tabId);
    });

    // Tab button click handler
    tabButton.addEventListener('click', () => switchTab(tabId));

    document.getElementById('tabs-container').appendChild(tabButton);

    // Create tab content
    const contentDiv = document.createElement('div');
    contentDiv.className = 'tab-content';
    contentDiv.id = `tab-${tabId}`;
    contentDiv.setAttribute('data-tab-id', tabId);
    contentDiv.innerHTML = `
        <div class="loading" id="loading-${tabId}">
            <div class="spinner"></div>
            <p>Loading data...</p>
        </div>
        <div class="content" id="content-${tabId}" style="display: none;">
            <h2 id="title-${tabId}"></h2>
            <p id="description-${tabId}" class="description"></p>
            <div class="filters-container" id="filters-${tabId}" style="display: none;"></div>
            <div class="chart-container" id="chart-${tabId}"></div>
            <div class="table-container" id="table-${tabId}"></div>
        </div>
        <div class="error" id="error-${tabId}" style="display: none;">
            <p id="error-msg-${tabId}"></p>
        </div>
    `;

    document.getElementById('tab-contents').appendChild(contentDiv);

    // Store in map
    openTabs.set(tabId, {
        button: tabButton,
        content: contentDiv
    });
}

function closeTab(tabId) {
    // Prevent closing last tab
    if (openTabs.size === 1) {
        alert('Cannot close the last tab');
        return;
    }

    const tab = openTabs.get(tabId);
    if (!tab) return;

    // Remove elements
    tab.button.remove();
    tab.content.remove();
    openTabs.delete(tabId);

    // Update sidebar
    updateSidebarHighlight(null);

    // If closing active tab, switch to another
    if (activeTabId === tabId) {
        const nextTabId = openTabs.keys().next().value;
        if (nextTabId) {
            switchTab(nextTabId);
        }
    }
}

function switchTab(tabId) {
    // Update active state
    openTabs.forEach((tab, id) => {
        if (id === tabId) {
            tab.button.classList.add('active');
            tab.content.classList.add('active');
            tab.content.style.display = 'block';
        } else {
            tab.button.classList.remove('active');
            tab.content.classList.remove('active');
            tab.content.style.display = 'none';
        }
    });

    activeTabId = tabId;
    updateSidebarHighlight(tabId);
    loadTabData(tabId);
}

function updateSidebarHighlight(tabId) {
    document.querySelectorAll('.sidebar-item').forEach(item => {
        if (tabId && item.getAttribute('data-tab-id') === tabId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

// ============================================================================
// DATA LOADING
// ============================================================================

function loadTabData(tabId) {
    const loading = document.getElementById(`loading-${tabId}`);
    const content = document.getElementById(`content-${tabId}`);
    const error = document.getElementById(`error-${tabId}`);

    // Show loading
    loading.style.display = 'flex';
    content.style.display = 'none';
    error.style.display = 'none';

    // Build query parameters
    const filters = getActiveFilters(tabId);
    const queryParams = new URLSearchParams(filters).toString();
    const apiUrl = `/api/data/${tabId}${queryParams ? '?' + queryParams : ''}`;

    // Fetch data
    fetch(apiUrl)
        .then(response => {
            if (!response.ok) throw new Error('Failed to load data');
            return response.json();
        })
        .then(data => {
            renderTabContent(tabId, data);
            loading.style.display = 'none';
            content.style.display = 'block';
        })
        .catch(err => {
            console.error('Error:', err);
            loading.style.display = 'none';
            error.style.display = 'block';
            document.getElementById(`error-msg-${tabId}`).textContent = err.message;
        });
}

function getActiveFilters(tabId) {
    const filters = {};
    const filterSelects = document.querySelectorAll(`#filters-${tabId} select`);
    filterSelects.forEach(select => {
        if (select.value) {
            filters[select.name] = select.value;
        }
    });
    return filters;
}

// ============================================================================
// RENDERING
// ============================================================================

function renderTabContent(tabId, data) {
    console.log(`Rendering tab content for ${tabId}`, data);

    document.getElementById(`title-${tabId}`).textContent = data.title;
    document.getElementById(`description-${tabId}`).textContent = data.description;

    if (data.filters_config && data.filters_config.length > 0) {
        renderFilters(tabId, data.filters_config);
    }

    // Always render chart if we have data
    if (data.chart_type) {
        console.log(`Chart type: ${data.chart_type}, config:`, data.chart_config);
        renderChart(tabId, data);
    } else {
        console.warn(`No chart type for tab ${tabId}`);
    }

    // Always render table - it's defined in the HTML
    renderTable(tabId, data);
}

function renderFilters(tabId, filtersConfig) {
    const container = document.getElementById(`filters-${tabId}`);
    if (!container) return;

    container.innerHTML = '';
    container.style.display = 'flex';

    filtersConfig.forEach(filter => {
        const group = document.createElement('div');
        group.className = 'filter-group';

        const label = document.createElement('label');
        label.textContent = filter.label || filter.column;

        const select = document.createElement('select');
        select.name = filter.column;

        const emptyOption = document.createElement('option');
        emptyOption.value = '';
        emptyOption.textContent = 'All';
        select.appendChild(emptyOption);

        // Load options from API
        fetch(`/api/filter-options/${tabId}/${filter.column}`)
            .then(res => res.json())
            .then(data => {
                if (data.options) {
                    data.options.forEach(opt => {
                        const option = document.createElement('option');
                        option.value = opt;
                        option.textContent = opt;
                        select.appendChild(option);
                    });
                }
            });

        select.addEventListener('change', () => loadTabData(tabId));

        group.appendChild(label);
        group.appendChild(select);
        container.appendChild(group);
    });

    // Reset button
    const resetBtn = document.createElement('button');
    resetBtn.className = 'filter-reset';
    resetBtn.textContent = 'Reset Filters';
    resetBtn.addEventListener('click', () => {
        container.querySelectorAll('select').forEach(s => s.value = '');
        loadTabData(tabId);
    });
    container.appendChild(resetBtn);
}

// ============================================================================
// CHART RENDERING
// ============================================================================

function renderChart(tabId, data) {
    const container = document.getElementById(`chart-${tabId}`);
    if (!container) {
        return;
    }

    container.innerHTML = '';

    try {
        if (!window.d3) {
            container.innerHTML = '<p style="color: #666; padding: 20px;">D3.js library not loaded</p>';
            return;
        }

        if (data.chart_type === 'bar') {
            renderBarChart(container, data);
        } else if (data.chart_type === 'pie') {
            renderPieChart(container, data);
        } else if (data.chart_type === 'line') {
            renderLineChart(container, data);
        }
    } catch (err) {
        console.error('Chart error:', err);
        container.innerHTML = `<div style="padding: 20px; color: #c33; background: #fee; border-radius: 4px;">Error rendering chart: ${err.message}</div>`;
    }
}

function renderBarChart(container, data) {
    if (!data || !data.data || data.data.length === 0) {
        container.innerHTML = '<p>No data available</p>';
        return;
    }

    const config = data.chart_config;
    const xAxis = config.x_axis;
    const yAxis = config.y_axis;

    if (!xAxis || !yAxis) {
        console.error('Missing x_axis or y_axis in chart config');
        return;
    }

    const xIsNumeric = typeof data.data[0][xAxis] === 'number';
    const yIsNumeric = typeof data.data[0][yAxis] === 'number';
    const isHorizontal = !yIsNumeric && xIsNumeric;

    const margin = isHorizontal
        ? { top: 20, right: 200, bottom: 30, left: 150 }
        : { top: 20, right: 200, bottom: 60, left: 70 };

    const width = 800 - margin.left - margin.right;
    const height = isHorizontal
        ? Math.max(400, data.data.length * 25)
        : 400;

    const svg = d3.select(container)
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    let scale1, scale2, valueField;

    if (isHorizontal) {
        scale1 = d3.scaleBand()
            .domain(data.data.map(d => d[yAxis]))
            .range([0, height])
            .padding(0.2);

        scale2 = d3.scaleLinear()
            .domain([0, d3.max(data.data, d => d[xAxis])])
            .range([0, width]);

        valueField = xAxis;
    } else {
        scale1 = d3.scaleBand()
            .domain(data.data.map(d => d[xAxis]))
            .range([0, width])
            .padding(0.2);

        scale2 = d3.scaleLinear()
            .domain([0, d3.max(data.data, d => d[yAxis])])
            .range([height, 0]);

        valueField = yAxis;
    }

    // Bars
    svg.selectAll('.bar')
        .data(data.data)
        .enter()
        .append('rect')
        .attr('class', 'bar')
        .attr('x', d => isHorizontal ? 0 : scale1(d[xAxis]))
        .attr('y', d => isHorizontal ? scale1(d[yAxis]) : scale2(d[yAxis]))
        .attr('width', d => isHorizontal ? scale2(d[xAxis]) : scale1.bandwidth())
        .attr('height', d => isHorizontal ? scale1.bandwidth() : height - scale2(d[yAxis]));

    // Values on bars
    if (config.show_values) {
        svg.selectAll('.bar-value')
            .data(data.data)
            .enter()
            .append('text')
            .attr('class', 'bar-value')
            .attr('x', d => isHorizontal
                ? scale2(d[xAxis]) + 5
                : scale1(d[xAxis]) + scale1.bandwidth() / 2)
            .attr('y', d => isHorizontal
                ? scale1(d[yAxis]) + scale1.bandwidth() / 2 + 5
                : scale2(d[yAxis]) - 5)
            .attr('text-anchor', isHorizontal ? 'start' : 'middle')
            .attr('font-size', '11px')
            .attr('fill', '#555')
            .text(d => d[valueField]);
    }

    // Axes
    if (isHorizontal) {
        svg.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(scale2));

        svg.append('g')
            .call(d3.axisLeft(scale1));
    } else {
        svg.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(scale1));

        svg.append('g')
            .call(d3.axisLeft(scale2));
    }

    // Title
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', -5)
        .attr('text-anchor', 'middle')
        .attr('font-size', '16px')
        .attr('font-weight', 'bold')
        .attr('fill', '#2c3e50')
        .text(config.title);

    // Legend
    const legend = svg.append('g')
        .attr('class', 'legend')
        .attr('transform', `translate(${width + 20}, 0)`);

    legend.append('rect')
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', 150)
        .attr('height', 70)
        .attr('fill', 'white')
        .attr('stroke', '#ddd')
        .attr('stroke-width', 1)
        .attr('rx', 4);

    legend.append('text')
        .attr('x', 8)
        .attr('y', 20)
        .attr('font-weight', 'bold')
        .attr('font-size', '12px')
        .attr('fill', '#2c3e50')
        .text('Legend');

    const legendItem = legend.append('g')
        .attr('transform', 'translate(8, 30)');

    legendItem.append('rect')
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', 12)
        .attr('height', 12)
        .attr('fill', '#87CEEB')
        .attr('opacity', 0.8);

    legendItem.append('text')
        .attr('x', 18)
        .attr('y', 10)
        .attr('font-size', '12px')
        .attr('fill', '#555')
        .text(yAxis);
}

function renderPieChart(container, data) {
    const config = data.chart_config;
    const xAxis = config.x_axis;
    const yAxis = config.y_axis;

    const width = 600;
    const height = 400;
    const radius = Math.min(width, height) / 2 - 60;

    const svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', `translate(${width / 2 - 50},${height / 2})`);

    const pie = d3.pie().value(d => d[yAxis]);
    const arc = d3.arc().innerRadius(0).outerRadius(radius);

    const colors = d3.scaleOrdinal(d3.schemeBlues[9]);

    svg.selectAll('.arc')
        .data(pie(data.data))
        .enter()
        .append('g')
        .attr('class', 'arc')
        .append('path')
        .attr('d', arc)
        .attr('fill', (d, i) => colors(i))
        .attr('opacity', 0.8);

    // Title
    svg.append('text')
        .attr('x', 0)
        .attr('y', -radius - 30)
        .attr('text-anchor', 'middle')
        .attr('font-size', '16px')
        .attr('font-weight', 'bold')
        .attr('fill', '#2c3e50')
        .text(config.title);

    // Legend
    const legend = svg.append('g')
        .attr('class', 'legend')
        .attr('transform', `translate(${radius + 30}, ${-radius + 20})`);

    const legendData = data.data.slice(0, 8); // Limit to 8 items for readability

    legendData.forEach((d, i) => {
        const legendRow = legend.append('g')
            .attr('transform', `translate(0, ${i * 20})`);

        legendRow.append('rect')
            .attr('x', 0)
            .attr('y', 0)
            .attr('width', 12)
            .attr('height', 12)
            .attr('fill', colors(i))
            .attr('opacity', 0.8);

        legendRow.append('text')
            .attr('x', 18)
            .attr('y', 10)
            .attr('font-size', '12px')
            .attr('fill', '#555')
            .text(String(d[xAxis]).substring(0, 20));
    });
}

function renderLineChart(container, data) {
    const config = data.chart_config;
    const xAxis = config.x_axis;
    const yAxis = config.y_axis;

    const margin = { top: 20, right: 200, bottom: 60, left: 70 };
    const width = 800 - margin.left - margin.right;
    const height = 400;

    const svg = d3.select(container)
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Scales
    const xScale = d3.scaleBand()
        .domain(data.data.map(d => d[xAxis]))
        .range([0, width])
        .padding(0.1);

    const yScale = d3.scaleLinear()
        .domain([0, d3.max(data.data, d => d[yAxis])])
        .range([height, 0]);

    // Line
    const line = d3.line()
        .x(d => xScale(d[xAxis]) + xScale.bandwidth() / 2)
        .y(d => yScale(d[yAxis]));

    svg.append('path')
        .datum(data.data)
        .attr('class', 'line')
        .attr('d', line);

    // Dots
    svg.selectAll('.dot')
        .data(data.data)
        .enter()
        .append('circle')
        .attr('class', 'dot')
        .attr('cx', d => xScale(d[xAxis]) + xScale.bandwidth() / 2)
        .attr('cy', d => yScale(d[yAxis]));

    // Axes
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(xScale));

    svg.append('g')
        .call(d3.axisLeft(yScale));

    // Title
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', -5)
        .attr('text-anchor', 'middle')
        .attr('font-size', '16px')
        .attr('font-weight', 'bold')
        .attr('fill', '#2c3e50')
        .text(config.title);

    // Legend
    const legend = svg.append('g')
        .attr('class', 'legend')
        .attr('transform', `translate(${width + 20}, 0)`);

    legend.append('rect')
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', 150)
        .attr('height', 90)
        .attr('fill', 'white')
        .attr('stroke', '#ddd')
        .attr('stroke-width', 1)
        .attr('rx', 4);

    legend.append('text')
        .attr('x', 8)
        .attr('y', 20)
        .attr('font-weight', 'bold')
        .attr('font-size', '12px')
        .attr('fill', '#2c3e50')
        .text('Legend');

    const lineLegend = legend.append('g')
        .attr('transform', 'translate(8, 30)');

    lineLegend.append('line')
        .attr('x1', 0)
        .attr('y1', 0)
        .attr('x2', 12)
        .attr('y2', 0)
        .attr('stroke', '#87CEEB')
        .attr('stroke-width', 2);

    lineLegend.append('text')
        .attr('x', 18)
        .attr('y', 4)
        .attr('font-size', '12px')
        .attr('fill', '#555')
        .text(yAxis);

    const dotLegend = legend.append('g')
        .attr('transform', 'translate(8, 55)');

    dotLegend.append('circle')
        .attr('cx', 6)
        .attr('cy', 0)
        .attr('r', 4)
        .attr('fill', '#87CEEB');

    dotLegend.append('text')
        .attr('x', 18)
        .attr('y', 4)
        .attr('font-size', '12px')
        .attr('fill', '#555')
        .text('Data Points');
}

// ============================================================================
// TABLE RENDERING
// ============================================================================

function renderTable(tabId, data) {
    const container = document.getElementById(`table-${tabId}`);
    if (!container) return;

    let html = '<table>';
    html += '<thead><tr>';
    data.columns.forEach(col => {
        html += `<th>${col}</th>`;
    });
    html += '</tr></thead>';
    html += '<tbody>';

    data.data.forEach(row => {
        html += '<tr>';
        data.columns.forEach(col => {
            html += `<td>${row[col]}</td>`;
        });
        html += '</tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}
