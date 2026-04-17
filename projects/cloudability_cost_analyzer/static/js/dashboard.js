// Reporting Engine Dashboard - JavaScript

// ============================================================================
// TAB MANAGEMENT
// ============================================================================

document.addEventListener('DOMContentLoaded', function () {
    initializeTabs();
});

function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', function () {
            const tabId = this.getAttribute('data-tab-id');
            switchTab(tabId, tabButtons, tabContents);
        });
    });

    // Load first tab
    if (tabButtons.length > 0) {
        const firstTabId = tabButtons[0].getAttribute('data-tab-id');
        switchTab(firstTabId, tabButtons, tabContents);
    }
}

function switchTab(tabId, tabButtons, tabContents) {
    // Update button states
    tabButtons.forEach(btn => {
        if (btn.getAttribute('data-tab-id') === tabId) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Update content visibility
    tabContents.forEach(content => {
        if (content.getAttribute('id') === `tab-${tabId}`) {
            content.classList.add('active');
            // Load data for this tab
            loadTabData(tabId);
        } else {
            content.classList.remove('active');
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

    // Build query parameters from filter values
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
// FILTER RENDERING
// ============================================================================

function renderFilters(tabId, filtersConfig) {
    const filtersContainer = document.getElementById(`filters-${tabId}`);
    if (!filtersContainer) return;

    filtersContainer.innerHTML = '';
    filtersContainer.style.display = 'flex';

    filtersConfig.forEach(filter => {
        const filterGroup = document.createElement('div');
        filterGroup.className = 'filter-group';

        const label = document.createElement('label');
        label.textContent = filter.label || filter.column;

        const select = document.createElement('select');
        select.name = filter.column;
        select.className = 'filter-select';

        // Add empty option
        const emptyOption = document.createElement('option');
        emptyOption.value = '';
        emptyOption.textContent = `All ${label.textContent}`;
        select.appendChild(emptyOption);

        // Load options from API
        loadFilterOptions(filter.table, filter.column, select, tabId);

        // Add event listener to reload on change
        select.addEventListener('change', () => {
            loadTabData(tabId);
        });

        filterGroup.appendChild(label);
        filterGroup.appendChild(select);
        filtersContainer.appendChild(filterGroup);
    });

    // Add reset button
    const resetBtn = document.createElement('button');
    resetBtn.className = 'filter-reset';
    resetBtn.textContent = 'Reset Filters';
    resetBtn.addEventListener('click', () => {
        const selects = filtersContainer.querySelectorAll('select');
        selects.forEach(s => s.value = '');
        loadTabData(tabId);
    });
    filtersContainer.appendChild(resetBtn);
}

function loadFilterOptions(tableName, columnName, selectElement, tabId) {
    fetch(`/api/filter-options/${tableName}/${columnName}`)
        .then(response => response.json())
        .then(data => {
            if (data.options) {
                data.options.forEach(option => {
                    const opt = document.createElement('option');
                    opt.value = option;
                    opt.textContent = option;
                    selectElement.appendChild(opt);
                });
            }
        })
        .catch(err => console.error('Error loading filter options:', err));
}

// ============================================================================
// RENDERING
// ============================================================================

function renderTabContent(tabId, data) {
    // Set title and description
    document.getElementById(`title-${tabId}`).textContent = data.title;
    document.getElementById(`description-${tabId}`).textContent = data.description;

    // Render filters if configured
    if (data.filters_config && data.filters_config.length > 0) {
        renderFilters(tabId, data.filters_config);
    }

    // Render chart if needed
    if (data.chart_type && data.chart_config) {
        renderChart(tabId, data);
    }

    // Render table if needed
    if (data.display_config && (data.display_config.type === 'table' || data.display_config.type === 'both')) {
        renderTable(tabId, data);
    }
}

// ============================================================================
// CHART RENDERING (D3.js)
// ============================================================================

function renderChart(tabId, data) {
    const chartContainer = document.getElementById(`chart-${tabId}`);
    chartContainer.innerHTML = ''; // Clear

    if (data.chart_type === 'bar') {
        renderBarChart(chartContainer, data);
    } else if (data.chart_type === 'pie') {
        renderPieChart(chartContainer, data);
    } else if (data.chart_type === 'line') {
        renderLineChart(chartContainer, data);
    }
}

function renderBarChart(container, data) {
    const config = data.chart_config;
    const xAxis = config.x_axis;
    const yAxis = config.y_axis;

    // Detect data types
    const xIsNumeric = typeof data.data[0][xAxis] === 'number';
    const yIsNumeric = typeof data.data[0][yAxis] === 'number';

    // Determine orientation: if y is categorical, render horizontal bars
    const isHorizontal = !yIsNumeric && xIsNumeric;

    // Dimensions
    const margin = isHorizontal
        ? { top: 20, right: 30, bottom: 30, left: 150 }  // More left margin for labels
        : { top: 20, right: 30, bottom: 60, left: 70 };   // More bottom margin for labels

    const width = 800 - margin.left - margin.right;
    const height = isHorizontal
        ? Math.max(400, data.data.length * 25)  // Scale height with data
        : 400;

    // SVG
    const svg = d3.select(container)
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Create scales based on orientation
    let scale1, scale2, valueField;

    if (isHorizontal) {
        // Horizontal bars: X = numeric (values), Y = categorical (categories)
        scale1 = d3.scaleBand()  // Y scale for categories
            .domain(data.data.map(d => d[yAxis]))
            .range([0, height])
            .padding(0.2);

        scale2 = d3.scaleLinear()  // X scale for values
            .domain([0, d3.max(data.data, d => d[xAxis])])
            .range([0, width]);

        valueField = xAxis;  // Value to display in tooltip
    } else {
        // Vertical bars: X = categorical (categories), Y = numeric (values)
        scale1 = d3.scaleBand()  // X scale for categories
            .domain(data.data.map(d => d[xAxis]))
            .range([0, width])
            .padding(0.2);

        scale2 = d3.scaleLinear()  // Y scale for values
            .domain([0, d3.max(data.data, d => d[yAxis])])
            .range([height, 0]);

        valueField = yAxis;  // Value to display in tooltip
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
        .attr('height', d => isHorizontal ? scale1.bandwidth() : height - scale2(d[yAxis]))
        .on('mouseover', function (event, d) {
            d3.select(this).style('opacity', 1);
            showTooltip(event, formatValue(d[valueField], data.format_config));
        })
        .on('mouseout', function () {
            d3.select(this).style('opacity', 0.8);
            hideTooltip();
        });

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
            .text(d => formatValue(d[valueField], data.format_config));
    }

    // Bottom/Left Axis
    if (isHorizontal) {
        // Horizontal: X axis at bottom, Y axis on left
        svg.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(scale2))
            .append('text')
            .attr('class', 'axis-label')
            .attr('x', width / 2)
            .attr('y', 25)
            .attr('text-anchor', 'middle')
            .attr('fill', '#555')
            .attr('font-size', '12px')
            .text(config.x_label || xAxis);

        svg.append('g')
            .call(d3.axisLeft(scale1))
            .append('text')
            .attr('class', 'axis-label')
            .attr('transform', 'rotate(-90)')
            .attr('x', -height / 2)
            .attr('y', -120)
            .attr('text-anchor', 'middle')
            .attr('fill', '#555')
            .attr('font-size', '12px')
            .text(config.y_label || yAxis);
    } else {
        // Vertical: X axis at bottom, Y axis on left
        svg.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(scale1))
            .append('text')
            .attr('class', 'axis-label')
            .attr('x', width / 2)
            .attr('y', 40)
            .attr('text-anchor', 'middle')
            .attr('fill', '#555')
            .attr('font-size', '12px')
            .text(config.x_label || xAxis);

        svg.append('g')
            .call(d3.axisLeft(scale2))
            .append('text')
            .attr('class', 'axis-label')
            .attr('transform', 'rotate(-90)')
            .attr('x', -height / 2)
            .attr('y', -50)
            .attr('text-anchor', 'middle')
            .attr('fill', '#555')
            .attr('font-size', '12px')
            .text(config.y_label || yAxis);
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
}

function renderPieChart(container, data) {
    const config = data.chart_config;
    const xAxis = config.x_axis;
    const yAxis = config.y_axis;

    const width = 400;
    const height = 400;
    const radius = Math.min(width, height) / 2 - 40;

    const svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', `translate(${width / 2},${height / 2})`);

    const pie = d3.pie().value(d => d[yAxis]);
    const arc = d3.arc().innerRadius(0).outerRadius(radius);

    // Sky blue color palette
    const skyBlueColors = [
        '#87CEEB', '#1E90FF', '#00BFFF', '#6BB6D6', '#5F9EA0',
        '#4682B4', '#70AD47', '#00CED1', '#20B2AA', '#3CB371'
    ];
    const colors = d3.scaleOrdinal(skyBlueColors);

    svg.selectAll('.arc')
        .data(pie(data.data))
        .enter()
        .append('g')
        .attr('class', 'arc')
        .append('path')
        .attr('d', arc)
        .attr('fill', (d, i) => colors(i))
        .attr('opacity', 0.8)
        .on('mouseover', function (event, d) {
            d3.select(this).attr('opacity', 1);
            const percentage = (d.data[yAxis] / d3.sum(data.data, d => d[yAxis]) * 100).toFixed(1);
            showTooltip(event, `${d.data[xAxis]}: ${percentage}%`);
        })
        .on('mouseout', function () {
            d3.select(this).attr('opacity', 0.8);
            hideTooltip();
        });

    // Labels
    if (config.show_percentage) {
        svg.selectAll('.label')
            .data(pie(data.data))
            .enter()
            .append('text')
            .attr('transform', d => `translate(${arc.centroid(d)})`)
            .attr('text-anchor', 'middle')
            .attr('font-size', '11px')
            .attr('fill', 'white')
            .attr('font-weight', 'bold')
            .text(d => {
                const percentage = (d.data[yAxis] / d3.sum(data.data, d => d[yAxis]) * 100).toFixed(0);
                return `${percentage}%`;
            });
    }

    // Legend
    if (config.show_legend) {
        const legend = svg.selectAll('.legend')
            .data(data.data)
            .enter()
            .append('g')
            .attr('class', 'legend')
            .attr('transform', (d, i) => `translate(0,${i * 20 - (data.data.length * 20) / 2})`);

        legend.append('rect')
            .attr('x', radius + 20)
            .attr('width', 12)
            .attr('height', 12)
            .attr('fill', (d, i) => colors(i));

        legend.append('text')
            .attr('x', radius + 40)
            .attr('y', 10)
            .attr('font-size', '11px')
            .text(d => d[xAxis]);
    }

    // Title
    svg.append('text')
        .attr('x', 0)
        .attr('y', -radius - 30)
        .attr('text-anchor', 'middle')
        .attr('font-size', '16px')
        .attr('font-weight', 'bold')
        .attr('fill', '#2c3e50')
        .text(config.title);
}

// ============================================================================
// TABLE RENDERING
// ============================================================================

function renderTable(tabId, data) {
    const tableContainer = document.getElementById(`table-${tabId}`);
    if (!tableContainer) return;

    let html = '<table>';

    // Header
    html += '<thead><tr>';
    data.columns.forEach(col => {
        html += `<th>${col}</th>`;
    });
    html += '</tr></thead>';

    // Body
    html += '<tbody>';
    data.data.forEach(row => {
        html += '<tr>';
        data.columns.forEach(col => {
            let value = row[col];
            // Format currency
            if (data.format_config && data.format_config.currency && col.includes('cost')) {
                value = formatCurrency(value);
            }
            // Format percentage
            if (col.includes('score') || col.includes('efficiency')) {
                value = value.toFixed(1) + '%';
            }
            html += `<td>${value}</td>`;
        });
        html += '</tr>';
    });
    html += '</tbody>';
    html += '</table>';

    tableContainer.innerHTML = html;
}

// ============================================================================
// FORMATTING & UTILITIES
// ============================================================================

function formatValue(value, formatConfig) {
    if (!formatConfig) return value;

    if (formatConfig.currency) {
        return formatCurrency(value);
    }
    if (formatConfig.add_percent_sign) {
        return value.toFixed(formatConfig.decimal_places || 1) + '%';
    }

    return value.toFixed(formatConfig.decimal_places || 0);
}

function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
}

// ============================================================================
// TOOLTIP
// ============================================================================

let tooltip = null;

function showTooltip(event, text) {
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        document.body.appendChild(tooltip);
    }

    tooltip.textContent = text;
    tooltip.style.display = 'block';
    tooltip.style.left = event.pageX + 10 + 'px';
    tooltip.style.top = event.pageY - 30 + 'px';
}

function hideTooltip() {
    if (tooltip) {
        tooltip.style.display = 'none';
    }
}

document.addEventListener('mousemove', function (event) {
    if (tooltip && tooltip.style.display !== 'none') {
        tooltip.style.left = event.pageX + 10 + 'px';
        tooltip.style.top = event.pageY - 30 + 'px';
    }
});
