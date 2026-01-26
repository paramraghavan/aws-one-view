/**
 * Snowflake Resource Monitor - JavaScript Application
 * Handles all dashboard interactions, API calls, and chart rendering
 */

// ============================================
// Global State
// ============================================

const state = {
    currentSection: 'overview',
    charts: {},
    queryData: {
        longRunning: [],
        expensive: [],
        queued: []
    }
};

// ============================================
// Chart Configuration
// ============================================

Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#2d3b4f';
Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";

const chartColors = {
    blue: '#29b6f6',
    cyan: '#00d4ff',
    teal: '#00bfa5',
    purple: '#a78bfa',
    orange: '#fb923c',
    red: '#f87171',
    green: '#4ade80',
    yellow: '#fbbf24'
};

const chartColorPalette = [
    chartColors.blue,
    chartColors.cyan,
    chartColors.teal,
    chartColors.purple,
    chartColors.orange,
    chartColors.green,
    chartColors.yellow,
    chartColors.red
];

// ============================================
// Utility Functions
// ============================================

function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined) return '--';
    if (typeof num !== 'number') num = parseFloat(num);
    if (isNaN(num)) return '--';
    
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toFixed(decimals);
}

function formatDate(dateStr) {
    if (!dateStr) return '--';
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatStorageSize(gb) {
    if (gb === null || gb === undefined || isNaN(gb)) return '--';
    if (gb >= 1024) {
        return (gb / 1024).toFixed(2) + ' TB';
    } else if (gb >= 1) {
        return gb.toFixed(1) + ' GB';
    } else {
        return (gb * 1024).toFixed(0) + ' MB';
    }
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span class="toast-message">${message}</span>`;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function truncateText(text, maxLength = 50) {
    if (!text) return '--';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

// ============================================
// Loading Overlay Functions
// ============================================

function showLoading(message = 'Loading data...') {
    const overlay = document.getElementById('loadingOverlay');
    const textEl = overlay.querySelector('.loading-text');
    if (textEl) textEl.textContent = message;
    overlay.classList.add('active');
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    overlay.classList.remove('active');
}

// ============================================
// API Functions
// ============================================

async function fetchAPI(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `/api/${endpoint}?${queryString}` : `/api/${endpoint}`;
    
    try {
        const response = await fetch(url);
        
        // Check if response is OK
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        // Check content type before parsing
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error(`Non-JSON response from ${endpoint}:`, text.substring(0, 200));
            throw new Error(`Server returned non-JSON response for ${endpoint}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'API request failed');
        }
        
        return data.data;
    } catch (error) {
        console.error(`Error fetching ${endpoint}:`, error);
        showToast(`Error: ${error.message}`, 'error');
        throw error;
    }
}

// ============================================
// Data Loading Functions
// ============================================

async function loadOverview() {
    showLoading('Loading overview metrics...');
    try {
        const [overview, costTrends, storage] = await Promise.all([
            fetchAPI('overview'),
            fetchAPI('cost-trends', { days: 30 }),
            fetchAPI('storage-usage')
        ]);
        
        // Update metric cards
        document.getElementById('totalCredits').textContent = formatNumber(overview.total_credits_30d, 1);
        document.getElementById('totalStorage').textContent = formatNumber(overview.total_storage_tb, 2);
        document.getElementById('queryCount').textContent = formatNumber(overview.queries_24h, 0);
        document.getElementById('activeWarehouses').textContent = overview.active_warehouses;
        document.getElementById('avgQueryTime').textContent = formatNumber(overview.avg_query_time_sec, 1);
        document.getElementById('failedQueries').textContent = formatNumber(overview.failed_queries_24h, 0);
        
        // Render cost trend chart
        renderCostTrendChart(costTrends);
        
        // Render storage chart
        renderStorageChart(storage);
        
        hideLoading();
    } catch (error) {
        console.error('Error loading overview:', error);
        hideLoading();
    }
}

async function loadCosts() {
    const days = document.getElementById('costDaysFilter').value;
    showLoading('Loading cost analysis...');
    
    try {
        const [warehouseCosts, databaseCosts, hourlyUsage] = await Promise.all([
            fetchAPI('warehouse-costs', { days }),
            fetchAPI('database-costs', { days }),
            fetchAPI('credit-usage-hourly', { days: 7 })
        ]);
        
        renderWarehouseCostChart(warehouseCosts);
        renderDatabaseCostChart(databaseCosts);
        renderHourlyUsageChart(hourlyUsage);
        renderWarehouseCostTable(warehouseCosts);
        
        hideLoading();
    } catch (error) {
        console.error('Error loading costs:', error);
        hideLoading();
    }
}

async function loadQueries() {
    const threshold = document.getElementById('queryThreshold').value;
    const limit = document.getElementById('queryLimit').value;
    showLoading('Loading query performance data...');
    
    try {
        const [longRunning, expensive, queued] = await Promise.all([
            fetchAPI('long-running-queries', { threshold, limit }),
            fetchAPI('expensive-queries', { days: 7, limit }),
            fetchAPI('queued-queries', { days: 7 })
        ]);
        
        state.queryData.longRunning = longRunning;
        state.queryData.expensive = expensive;
        state.queryData.queued = queued;
        
        renderLongRunningTable(longRunning);
        renderExpensiveTable(expensive);
        renderQueuedTable(queued);
        
        hideLoading();
    } catch (error) {
        console.error('Error loading queries:', error);
        hideLoading();
    }
}

async function loadWarehouses() {
    showLoading('Loading warehouse configurations...');
    try {
        const [configs, clusterLoad] = await Promise.all([
            fetchAPI('warehouse-config'),
            fetchAPI('cluster-load', { days: 7 })
        ]);
        
        renderWarehouseConfigTable(configs);
        renderClusterLoadChart(clusterLoad);
        
        hideLoading();
    } catch (error) {
        console.error('Error loading warehouses:', error);
        hideLoading();
    }
}

async function loadBottlenecks() {
    showLoading('Analyzing bottlenecks...');
    try {
        const [bottlenecks, patterns] = await Promise.all([
            fetchAPI('bottleneck-analysis'),
            fetchAPI('query-patterns', { days: 7 })
        ]);
        
        renderBottleneckCards(bottlenecks);
        renderQueryPatternChart(patterns.hourly);
        renderQueryTypeChart(patterns.by_type);
        
        hideLoading();
    } catch (error) {
        console.error('Error loading bottlenecks:', error);
        hideLoading();
    }
}

async function loadRecommendations() {
    showLoading('Generating recommendations...');
    try {
        const recommendations = await fetchAPI('recommendations');
        renderRecommendations(recommendations);
        hideLoading();
    } catch (error) {
        console.error('Error loading recommendations:', error);
        hideLoading();
    }
}

// ============================================
// Chart Rendering Functions
// ============================================

function renderCostTrendChart(data) {
    const ctx = document.getElementById('costTrendChart').getContext('2d');
    
    if (state.charts.costTrend) {
        state.charts.costTrend.destroy();
    }
    
    const labels = data.map(d => {
        const date = new Date(d.DATE);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    state.charts.costTrend = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Total Credits',
                    data: data.map(d => d.TOTAL_CREDITS),
                    borderColor: chartColors.blue,
                    backgroundColor: 'rgba(41, 182, 246, 0.1)',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Compute',
                    data: data.map(d => d.COMPUTE_CREDITS),
                    borderColor: chartColors.teal,
                    backgroundColor: 'transparent',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(45, 59, 79, 0.5)' }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

function renderStorageChart(data) {
    const ctx = document.getElementById('storageChart').getContext('2d');
    
    if (state.charts.storage) {
        state.charts.storage.destroy();
    }
    
    const sortedData = data.sort((a, b) => b.TOTAL_GB - a.TOTAL_GB).slice(0, 8);
    
    state.charts.storage = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: sortedData.map(d => d.DATABASE_NAME || 'Unknown'),
            datasets: [{
                data: sortedData.map(d => d.TOTAL_GB),
                backgroundColor: chartColorPalette,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { usePointStyle: true }
                }
            }
        }
    });
}

function renderWarehouseCostChart(data) {
    const ctx = document.getElementById('warehouseCostChart').getContext('2d');
    
    if (state.charts.warehouseCost) {
        state.charts.warehouseCost.destroy();
    }
    
    const sortedData = data.sort((a, b) => b.TOTAL_CREDITS - a.TOTAL_CREDITS).slice(0, 10);
    
    state.charts.warehouseCost = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sortedData.map(d => d.WAREHOUSE_NAME),
            datasets: [
                {
                    label: 'Compute Credits',
                    data: sortedData.map(d => d.COMPUTE_CREDITS),
                    backgroundColor: chartColors.blue
                },
                {
                    label: 'Cloud Services',
                    data: sortedData.map(d => d.CLOUD_SERVICES_CREDITS),
                    backgroundColor: chartColors.purple
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: { display: false }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    grid: { color: 'rgba(45, 59, 79, 0.5)' }
                }
            }
        }
    });
}

function renderDatabaseCostChart(data) {
    const ctx = document.getElementById('databaseCostChart').getContext('2d');
    
    if (state.charts.databaseCost) {
        state.charts.databaseCost.destroy();
    }
    
    const sortedData = data.sort((a, b) => b.TOTAL_HOURS - a.TOTAL_HOURS).slice(0, 8);
    
    state.charts.databaseCost = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: sortedData.map(d => d.DATABASE_NAME || 'Unknown'),
            datasets: [{
                data: sortedData.map(d => d.TOTAL_HOURS),
                backgroundColor: chartColorPalette,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { usePointStyle: true }
                }
            }
        }
    });
}

function renderHourlyUsageChart(data) {
    const ctx = document.getElementById('hourlyUsageChart').getContext('2d');
    
    if (state.charts.hourlyUsage) {
        state.charts.hourlyUsage.destroy();
    }
    
    // Aggregate by hour
    const hourlyAgg = {};
    data.forEach(d => {
        const hour = d.HOUR_OF_DAY;
        if (!hourlyAgg[hour]) {
            hourlyAgg[hour] = { total: 0, count: 0 };
        }
        hourlyAgg[hour].total += d.AVG_CREDITS || 0;
        hourlyAgg[hour].count++;
    });
    
    const labels = Array.from({ length: 24 }, (_, i) => `${i}:00`);
    const values = labels.map((_, i) => {
        const agg = hourlyAgg[i];
        return agg ? agg.total / agg.count : 0;
    });
    
    state.charts.hourlyUsage = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Avg Credits',
                data: values,
                backgroundColor: chartColors.cyan,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(45, 59, 79, 0.5)' }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

function renderClusterLoadChart(data) {
    const ctx = document.getElementById('clusterLoadChart').getContext('2d');
    
    if (state.charts.clusterLoad) {
        state.charts.clusterLoad.destroy();
    }
    
    // Group by warehouse
    const warehouses = [...new Set(data.map(d => d.WAREHOUSE_NAME))];
    const datasets = warehouses.slice(0, 5).map((wh, i) => {
        const whData = data.filter(d => d.WAREHOUSE_NAME === wh);
        return {
            label: wh,
            data: whData.map(d => ({
                x: new Date(d.HOUR),
                y: d.AVG_CONCURRENT_QUERIES || 0
            })),
            borderColor: chartColorPalette[i],
            backgroundColor: 'transparent',
            tension: 0.4
        };
    });
    
    state.charts.clusterLoad = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'day' },
                    grid: { display: false }
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Concurrent Queries' },
                    grid: { color: 'rgba(45, 59, 79, 0.5)' }
                }
            }
        }
    });
}

function renderQueryPatternChart(data) {
    const ctx = document.getElementById('queryPatternChart').getContext('2d');
    
    if (state.charts.queryPattern) {
        state.charts.queryPattern.destroy();
    }
    
    const labels = Array.from({ length: 24 }, (_, i) => `${i}:00`);
    const hourMap = {};
    data.forEach(d => {
        hourMap[d.HOUR_OF_DAY] = d.QUERY_COUNT;
    });
    
    state.charts.queryPattern = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Query Count',
                data: labels.map((_, i) => hourMap[i] || 0),
                backgroundColor: chartColors.purple,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(45, 59, 79, 0.5)' }
                },
                x: { grid: { display: false } }
            }
        }
    });
}

function renderQueryTypeChart(data) {
    const ctx = document.getElementById('queryTypeChart').getContext('2d');
    
    if (state.charts.queryType) {
        state.charts.queryType.destroy();
    }
    
    const sortedData = data.sort((a, b) => b.QUERY_COUNT - a.QUERY_COUNT).slice(0, 8);
    
    state.charts.queryType = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: sortedData.map(d => d.QUERY_TYPE),
            datasets: [{
                data: sortedData.map(d => d.QUERY_COUNT),
                backgroundColor: chartColorPalette,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { usePointStyle: true }
                }
            }
        }
    });
}

// ============================================
// Table Rendering Functions
// ============================================

function renderWarehouseCostTable(data) {
    const tbody = document.querySelector('#warehouseCostTable tbody');
    tbody.innerHTML = data.map(row => `
        <tr>
            <td><strong>${row.WAREHOUSE_NAME}</strong></td>
            <td>${formatNumber(row.TOTAL_CREDITS)} <span class="unit">credits</span></td>
            <td>${formatNumber(row.COMPUTE_CREDITS)} <span class="unit">credits</span></td>
            <td>${formatNumber(row.CLOUD_SERVICES_CREDITS)} <span class="unit">credits</span></td>
            <td>${row.ACTIVE_DAYS} <span class="unit">days</span></td>
            <td>${formatNumber(row.AVG_HOURLY_CREDITS, 3)} <span class="unit">credits/hr</span></td>
        </tr>
    `).join('');
}

function renderLongRunningTable(data) {
    const tbody = document.querySelector('#longRunningTable tbody');
    tbody.innerHTML = data.map(row => `
        <tr>
            <td><span class="query-id" data-query="${encodeURIComponent(row.QUERY_TEXT || '')}">${truncateText(row.QUERY_ID, 20)}</span></td>
            <td>${row.USER_NAME || '--'}</td>
            <td>${row.WAREHOUSE_NAME || '--'}</td>
            <td>${row.DATABASE_NAME || '--'}</td>
            <td>${formatNumber(row.ELAPSED_SECONDS, 1)} <span class="unit">sec</span></td>
            <td>${formatNumber(row.GB_SCANNED, 2)} <span class="unit">GB</span></td>
            <td>${formatNumber((row.QUEUED_OVERLOAD_SECONDS || 0) + (row.QUEUED_PROVISIONING_SECONDS || 0), 1)} <span class="unit">sec</span></td>
            <td><span class="status-badge ${(row.EXECUTION_STATUS || '').toLowerCase()}">${row.EXECUTION_STATUS || '--'}</span></td>
        </tr>
    `).join('');
    
    attachQueryIdListeners();
}

function renderExpensiveTable(data) {
    const tbody = document.querySelector('#expensiveTable tbody');
    tbody.innerHTML = data.map(row => `
        <tr>
            <td><span class="query-id" data-query="${encodeURIComponent(row.QUERY_TEXT || '')}">${truncateText(row.QUERY_ID, 20)}</span></td>
            <td>${row.USER_NAME || '--'}</td>
            <td>${row.WAREHOUSE_NAME || '--'}</td>
            <td>${row.DATABASE_NAME || '--'}</td>
            <td>${formatNumber(row.ELAPSED_SECONDS, 1)} <span class="unit">sec</span></td>
            <td>${formatNumber(row.GB_SCANNED, 2)} <span class="unit">GB</span></td>
            <td>${formatNumber(row.GB_WRITTEN, 2)} <span class="unit">GB</span></td>
            <td>${formatNumber(row.ROWS_PRODUCED, 0)} <span class="unit">rows</span></td>
        </tr>
    `).join('');
    
    attachQueryIdListeners();
}

function renderQueuedTable(data) {
    const tbody = document.querySelector('#queuedTable tbody');
    tbody.innerHTML = data.map(row => `
        <tr>
            <td><span class="query-id" data-query="${encodeURIComponent(row.QUERY_TEXT || '')}">${truncateText(row.QUERY_ID, 20)}</span></td>
            <td>${row.USER_NAME || '--'}</td>
            <td>${row.WAREHOUSE_NAME || '--'}</td>
            <td>${formatNumber(row.TOTAL_SEC, 1)} <span class="unit">sec</span></td>
            <td>${formatNumber(row.QUEUE_SEC, 1)} <span class="unit">sec</span></td>
            <td>${formatNumber(row.PROVISIONING_SEC, 1)} <span class="unit">sec</span></td>
            <td>${formatNumber(row.EXECUTION_SEC, 1)} <span class="unit">sec</span></td>
        </tr>
    `).join('');
    
    attachQueryIdListeners();
}

function renderWarehouseConfigTable(data) {
    const tbody = document.querySelector('#warehouseConfigTable tbody');
    tbody.innerHTML = data.map(row => `
        <tr>
            <td><strong>${row.WAREHOUSE_NAME}</strong></td>
            <td><span class="state-badge ${(row.STATE || '').toLowerCase()}">${row.STATE || '--'}</span></td>
            <td>${row.SIZE || '--'}</td>
            <td>${row.TYPE || '--'}</td>
            <td>${row.MIN_CLUSTER_COUNT || '--'}</td>
            <td>${row.MAX_CLUSTER_COUNT || '--'}</td>
            <td>${row.SCALING_POLICY || '--'}</td>
            <td>${row.AUTO_SUSPEND || '--'} <span class="unit">sec</span></td>
            <td>${row.AUTO_RESUME ? 'Yes' : 'No'}</td>
        </tr>
    `).join('');
}

// ============================================
// Bottleneck Rendering
// ============================================

function renderBottleneckCards(data) {
    // Queuing bottleneck
    const queuingEl = document.getElementById('queuingBottleneck');
    if (data.queuing && data.queuing.length > 0) {
        queuingEl.innerHTML = data.queuing.slice(0, 3).map(item => `
            <div class="bottleneck-item">
                <div class="warehouse-name">${item.WAREHOUSE_NAME}</div>
                <div class="bottleneck-stats">
                    ${formatNumber(item.QUEUED_QUERIES, 0)} queued queries • 
                    Avg: ${formatNumber(item.AVG_QUEUE_TIME_SEC, 1)}s • 
                    Max: ${formatNumber(item.MAX_QUEUE_TIME_SEC, 1)}s
                </div>
            </div>
        `).join('');
    } else {
        queuingEl.innerHTML = '<div class="bottleneck-empty">No significant queuing detected</div>';
    }
    
    // Spilling bottleneck
    const spillingEl = document.getElementById('spillingBottleneck');
    if (data.spilling && data.spilling.length > 0) {
        spillingEl.innerHTML = data.spilling.slice(0, 3).map(item => `
            <div class="bottleneck-item">
                <div class="warehouse-name">${item.WAREHOUSE_NAME}</div>
                <div class="bottleneck-stats">
                    ${formatNumber(item.SPILLING_QUERIES, 0)} queries spilled • 
                    Local: ${formatNumber(item.GB_SPILLED_LOCAL, 2)} GB • 
                    Remote: ${formatNumber(item.GB_SPILLED_REMOTE, 2)} GB
                </div>
            </div>
        `).join('');
    } else {
        spillingEl.innerHTML = '<div class="bottleneck-empty">No significant spilling detected</div>';
    }
    
    // Compilation bottleneck
    const compilationEl = document.getElementById('compilationBottleneck');
    if (data.compilation && data.compilation.length > 0) {
        compilationEl.innerHTML = data.compilation.slice(0, 3).map(item => `
            <div class="bottleneck-item">
                <div class="warehouse-name">${item.WAREHOUSE_NAME}</div>
                <div class="bottleneck-stats">
                    ${formatNumber(item.HIGH_COMPILE_QUERIES, 0)} high-compile queries • 
                    Avg: ${formatNumber(item.AVG_COMPILE_SEC, 1)}s • 
                    Max: ${formatNumber(item.MAX_COMPILE_SEC, 1)}s
                </div>
            </div>
        `).join('');
    } else {
        compilationEl.innerHTML = '<div class="bottleneck-empty">No high compilation times detected</div>';
    }
    
    // Failures bottleneck
    const failuresEl = document.getElementById('failuresBottleneck');
    if (data.failures && data.failures.length > 0) {
        failuresEl.innerHTML = data.failures.slice(0, 3).map(item => `
            <div class="bottleneck-item">
                <div class="warehouse-name">Error: ${item.ERROR_CODE || 'Unknown'}</div>
                <div class="bottleneck-stats">
                    ${formatNumber(item.FAILURE_COUNT, 0)} failures • 
                    ${truncateText(item.ERROR_MESSAGE, 60)}
                </div>
            </div>
        `).join('');
    } else {
        failuresEl.innerHTML = '<div class="bottleneck-empty">No query failures detected</div>';
    }
}

// ============================================
// Recommendations Rendering
// ============================================

function renderRecommendations(data) {
    const container = document.getElementById('recommendationsContainer');
    
    if (!data || data.length === 0) {
        container.innerHTML = `
            <div class="recommendation-card low">
                <div class="recommendation-header">
                    <span class="recommendation-title">No issues detected</span>
                    <span class="recommendation-category">Status</span>
                </div>
                <p class="recommendation-description">
                    Your Snowflake environment appears to be well-optimized. 
                    Continue monitoring for any changes in usage patterns.
                </p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = data.map(rec => `
        <div class="recommendation-card ${rec.severity.toLowerCase()}">
            <div class="recommendation-header">
                <span class="recommendation-title">${rec.title}</span>
                <span class="recommendation-category">${rec.category}</span>
            </div>
            <p class="recommendation-description">${rec.description}</p>
            ${rec.warehouse ? `<div class="recommendation-warehouse">Warehouse: ${rec.warehouse}</div>` : ''}
        </div>
    `).join('');
}

// ============================================
// Modal Functions
// ============================================

function showQueryModal(queryText) {
    const modal = document.getElementById('queryModal');
    const queryTextEl = document.getElementById('queryText');
    
    queryTextEl.textContent = decodeURIComponent(queryText);
    modal.classList.add('active');
}

function hideQueryModal() {
    const modal = document.getElementById('queryModal');
    modal.classList.remove('active');
}

function attachQueryIdListeners() {
    document.querySelectorAll('.query-id').forEach(el => {
        el.addEventListener('click', () => {
            const queryText = el.dataset.query;
            if (queryText) {
                showQueryModal(queryText);
            }
        });
    });
}

// ============================================
// NEEDS ATTENTION (Combined: Bottlenecks + Optimization + Recommendations)
// ============================================

async function loadAttention() {
    showLoading('Loading issues...');
    try {
        // Load each API separately to handle individual failures
        let bottlenecks = { queuing: [], spilling: [], compilation: [], failures: [] };
        let recommendations = [];
        let optimization = [];
        
        try {
            bottlenecks = await fetchAPI('bottleneck-analysis');
        } catch (e) {
            console.warn('Failed to load bottleneck-analysis:', e);
        }
        
        try {
            recommendations = await fetchAPI('recommendations');
        } catch (e) {
            console.warn('Failed to load recommendations:', e);
        }
        
        try {
            optimization = await fetchAPI('optimization-opportunities');
        } catch (e) {
            console.warn('Failed to load optimization-opportunities:', e);
        }
        
        // Categorize issues
        const critical = [];
        const warnings = [];
        const optimizations = [];
        
        // Process bottlenecks (ensure object exists)
        if (bottlenecks && typeof bottlenecks === 'object') {
            if (Array.isArray(bottlenecks.queuing)) {
                bottlenecks.queuing.forEach(q => {
                    if (q.AVG_QUEUE_TIME_SEC > 30) {
                        critical.push({
                            text: `${q.WAREHOUSE_NAME}: High queue time (avg ${formatNumber(q.AVG_QUEUE_TIME_SEC, 1)}s)`,
                            metric: `${formatNumber(q.QUEUED_QUERIES, 0)} queries queued`
                        });
                    } else if (q.AVG_QUEUE_TIME_SEC > 10) {
                        warnings.push({
                            text: `${q.WAREHOUSE_NAME}: Moderate queue time (avg ${formatNumber(q.AVG_QUEUE_TIME_SEC, 1)}s)`,
                            metric: `${formatNumber(q.QUEUED_QUERIES, 0)} queries queued`
                        });
                    }
                });
            }
            
            if (Array.isArray(bottlenecks.spilling)) {
                bottlenecks.spilling.forEach(s => {
                    if (s.GB_SPILLED_REMOTE > 10) {
                        critical.push({
                            text: `${s.WAREHOUSE_NAME}: Heavy remote spilling (expensive!)`,
                            metric: `${formatNumber(s.GB_SPILLED_REMOTE, 1)} GB remote spill`
                        });
                    } else if (s.GB_SPILLED_LOCAL > 50) {
                        warnings.push({
                            text: `${s.WAREHOUSE_NAME}: High local spilling`,
                            metric: `${formatNumber(s.GB_SPILLED_LOCAL, 1)} GB local spill`
                        });
                    }
                });
            }
            
            if (Array.isArray(bottlenecks.failures) && bottlenecks.failures.length > 0) {
                bottlenecks.failures.forEach(f => {
                    if (f.FAILURE_COUNT > 100) {
                        critical.push({
                            text: `Query failures: ${truncateText(f.ERROR_MESSAGE, 50)}`,
                            metric: `${formatNumber(f.FAILURE_COUNT, 0)} failures`
                        });
                    } else if (f.FAILURE_COUNT > 20) {
                        warnings.push({
                            text: `Query failures: ${truncateText(f.ERROR_MESSAGE, 50)}`,
                            metric: `${formatNumber(f.FAILURE_COUNT, 0)} failures`
                        });
                    }
                });
            }
        }
        
        // Process recommendations (ensure it's an array)
        if (Array.isArray(recommendations)) {
            recommendations.forEach(rec => {
                if (rec.severity === 'High') {
                    critical.push({
                        text: rec.title + ': ' + truncateText(rec.description, 80),
                        metric: rec.warehouse || rec.category
                    });
                } else if (rec.severity === 'Medium') {
                    warnings.push({
                        text: rec.title + ': ' + truncateText(rec.description, 80),
                        metric: rec.warehouse || rec.category
                    });
                } else {
                    optimizations.push({
                        text: rec.title + ': ' + truncateText(rec.description, 80),
                        metric: rec.warehouse || rec.category
                    });
                }
            });
        }
        
        // Add optimization opportunities summary (ensure it's an array)
        const issueTypes = {};
        if (Array.isArray(optimization)) {
            optimization.forEach(opt => {
                const type = opt.ISSUE_TYPE;
                if (!issueTypes[type]) {
                    issueTypes[type] = { count: 0, totalSec: 0 };
                }
                issueTypes[type].count++;
                issueTypes[type].totalSec += opt.ELAPSED_SEC || 0;
            });
        }
        
        Object.entries(issueTypes).forEach(([type, data]) => {
            optimizations.push({
                text: `${type}: ${data.count} queries could be optimized`,
                metric: `${formatNumber(data.totalSec / 60, 0)} min total`
            });
        });
        
        // Render sections
        renderAttentionList('criticalIssues', critical, 'critical');
        renderAttentionList('warningIssues', warnings, 'warning');
        renderAttentionList('optimizationIssues', optimizations, '');
        
        // Render top queries to fix
        renderAttentionQueriesTable(Array.isArray(optimization) ? optimization.slice(0, 10) : []);
        
        hideLoading();
    } catch (error) {
        console.error('Error loading attention:', error);
        // Show error state in the UI
        renderAttentionList('criticalIssues', [], 'critical');
        renderAttentionList('warningIssues', [], 'warning');
        renderAttentionList('optimizationIssues', [], '');
        renderAttentionQueriesTable([]);
        showToast('Failed to load attention data', 'error');
        hideLoading();
    }
}

function renderAttentionList(containerId, items, className) {
    const container = document.getElementById(containerId);
    
    if (!items || items.length === 0) {
        container.innerHTML = '<p class="no-data">No issues found ✓</p>';
        return;
    }
    
    container.innerHTML = items.map(item => `
        <div class="attention-item ${className}">
            <span class="issue-text">${item.text}</span>
            <span class="issue-metric">${item.metric}</span>
        </div>
    `).join('');
}

function renderAttentionQueriesTable(queries) {
    const tbody = document.querySelector('#attentionQueriesTable tbody');
    
    if (!queries || queries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-data">No problematic queries found</td></tr>';
        return;
    }
    
    tbody.innerHTML = queries.map(q => `
        <tr>
            <td><span class="query-id clickable-query" data-query="${encodeURIComponent(q.QUERY_TEXT || '')}">${truncateText(q.QUERY_ID, 15)}</span></td>
            <td><span class="issue-badge ${q.ISSUE_TYPE.toLowerCase().replace(/\s+/g, '-')}">${q.ISSUE_TYPE}</span></td>
            <td>${q.USER_NAME || '--'}</td>
            <td>${formatNumber(q.ELAPSED_SEC, 0)} <span class="unit">sec</span></td>
            <td class="recommendation-cell">${q.RECOMMENDATION || 'Review query'}</td>
        </tr>
    `).join('');
    
    attachQueryIdListeners();
}

// ============================================
// Navigation Functions
// ============================================

function switchSection(sectionId) {
    // Update navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.section === sectionId);
    });
    
    // Update content sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.toggle('active', section.id === sectionId);
    });
    
    state.currentSection = sectionId;
    
    // Load section data
    loadSectionData(sectionId);
}

function loadSectionData(sectionId) {
    switch (sectionId) {
        case 'overview':
            loadOverview();
            break;
        case 'attention':
            loadAttention();
            break;
        case 'database':
            loadDatabaseList();
            break;
        case 'warehouses':
            loadWarehouses();
            break;
        case 'users':
            loadUsersAndSecurity();
            break;
    }
}

// ============================================
// Event Listeners
// ============================================

function initEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            switchSection(item.dataset.section);
        });
    });
    
    // Refresh button
    document.getElementById('refreshBtn').addEventListener('click', async () => {
        const btn = document.getElementById('refreshBtn');
        btn.classList.add('loading');
        
        await loadSectionData(state.currentSection);
        
        btn.classList.remove('loading');
        document.getElementById('lastRefresh').textContent = new Date().toLocaleTimeString();
        showToast('Data refreshed successfully');
    });
    
    // Cost filter
    document.getElementById('costDaysFilter').addEventListener('change', loadCosts);
    
    // Query filters
    document.getElementById('applyQueryFilters').addEventListener('click', loadQueries);
    
    // Query tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
        });
    });
    
    // Modal close
    document.querySelector('.modal-close').addEventListener('click', hideQueryModal);
    document.getElementById('queryModal').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) {
            hideQueryModal();
        }
    });
    
    // Keyboard shortcut for modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            hideQueryModal();
        }
    });
    
    // Database Deep Dive - Load button
    document.getElementById('loadDatabaseBtn').addEventListener('click', loadDatabaseAnalysis);
    
    // Database tabs
    document.querySelectorAll('.db-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.db-tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.db-tab-content').forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
        });
    });
}

// ============================================
// NEW FEATURE: Cost Forecast
// ============================================

async function loadForecast() {
    showLoading('Loading cost forecast...');
    try {
        const [forecast, weekComparison] = await Promise.all([
            fetchAPI('cost-forecast', { days: 30 }),
            fetchAPI('week-over-week')
        ]);
        
        // Update metrics
        document.getElementById('avgDailyCredits').textContent = formatNumber(forecast.forecast.avg_daily_credits, 1);
        document.getElementById('projectedCredits').textContent = formatNumber(forecast.forecast.projected_30_day, 0);
        document.getElementById('trendDirection').textContent = forecast.forecast.trend_direction.charAt(0).toUpperCase() + forecast.forecast.trend_direction.slice(1);
        document.getElementById('trendFactor').textContent = `(${formatNumber((forecast.forecast.trend_factor - 1) * 100, 1)}%)`;
        document.getElementById('weekChangeCredits').textContent = formatNumber(weekComparison.credit_change_pct, 1);
        
        // Render daily credits chart
        renderDailyCreditsChart(forecast.daily_data);
        
        // Render week comparison
        renderWeekComparison(weekComparison);
        
        hideLoading();
    } catch (error) {
        console.error('Error loading forecast:', error);
        hideLoading();
    }
}

function renderDailyCreditsChart(data) {
    const ctx = document.getElementById('dailyCreditsChart').getContext('2d');
    
    if (state.charts.dailyCredits) {
        state.charts.dailyCredits.destroy();
    }
    
    state.charts.dailyCredits = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.DATE),
            datasets: [
                {
                    label: 'Total Credits',
                    data: data.map(d => d.DAILY_CREDITS),
                    borderColor: chartColors.cyan,
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Compute',
                    data: data.map(d => d.COMPUTE_CREDITS),
                    borderColor: chartColors.blue,
                    backgroundColor: 'transparent',
                    borderDash: [5, 5],
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' }
            },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Credits' } }
            }
        }
    });
}

function renderWeekComparison(data) {
    const container = document.getElementById('weekComparisonGrid');
    
    const thisWeek = data.queries.find(q => q.PERIOD === 'This Week') || {};
    const lastWeek = data.queries.find(q => q.PERIOD === 'Last Week') || {};
    
    const calcChange = (current, previous) => {
        if (!previous || previous === 0) return 0;
        return ((current - previous) / previous) * 100;
    };
    
    const formatChange = (pct) => {
        const sign = pct >= 0 ? '+' : '';
        const color = pct > 5 ? 'var(--accent-red)' : (pct < -5 ? 'var(--accent-green)' : 'var(--text-secondary)');
        return `<span style="color: ${color}">${sign}${formatNumber(pct, 1)}%</span>`;
    };
    
    container.innerHTML = `
        <div class="comparison-card">
            <h4>Credits</h4>
            <div class="comparison-values">
                <div class="this-week">
                    <span class="label">This Week</span>
                    <span class="value">${formatNumber(data.credits[0]?.THIS_WEEK_CREDITS, 0)}</span>
                </div>
                <div class="change">${formatChange(data.credit_change_pct)}</div>
                <div class="last-week">
                    <span class="label">Last Week</span>
                    <span class="value">${formatNumber(data.credits[0]?.LAST_WEEK_CREDITS, 0)}</span>
                </div>
            </div>
        </div>
        <div class="comparison-card">
            <h4>Queries</h4>
            <div class="comparison-values">
                <div class="this-week">
                    <span class="label">This Week</span>
                    <span class="value">${formatNumber(thisWeek.QUERY_COUNT, 0)}</span>
                </div>
                <div class="change">${formatChange(calcChange(thisWeek.QUERY_COUNT, lastWeek.QUERY_COUNT))}</div>
                <div class="last-week">
                    <span class="label">Last Week</span>
                    <span class="value">${formatNumber(lastWeek.QUERY_COUNT, 0)}</span>
                </div>
            </div>
        </div>
        <div class="comparison-card">
            <h4>Avg Duration</h4>
            <div class="comparison-values">
                <div class="this-week">
                    <span class="label">This Week</span>
                    <span class="value">${formatNumber(thisWeek.AVG_DURATION_SEC, 1)}s</span>
                </div>
                <div class="change">${formatChange(calcChange(thisWeek.AVG_DURATION_SEC, lastWeek.AVG_DURATION_SEC))}</div>
                <div class="last-week">
                    <span class="label">Last Week</span>
                    <span class="value">${formatNumber(lastWeek.AVG_DURATION_SEC, 1)}s</span>
                </div>
            </div>
        </div>
        <div class="comparison-card">
            <h4>Active Users</h4>
            <div class="comparison-values">
                <div class="this-week">
                    <span class="label">This Week</span>
                    <span class="value">${data.users[0]?.THIS_WEEK_USERS || '--'}</span>
                </div>
                <div class="change">${formatChange(calcChange(data.users[0]?.THIS_WEEK_USERS, data.users[0]?.LAST_WEEK_USERS))}</div>
                <div class="last-week">
                    <span class="label">Last Week</span>
                    <span class="value">${data.users[0]?.LAST_WEEK_USERS || '--'}</span>
                </div>
            </div>
        </div>
    `;
}

// ============================================
// NEW FEATURE: User Analytics
// ============================================

async function loadUsersAndSecurity() {
    showLoading('Loading users & security...');
    try {
        const [userData, securityData] = await Promise.all([
            fetchAPI('user-analytics', { days: 30 }),
            fetchAPI('login-history', { days: 7 })
        ]);
        
        // User analytics
        renderUserActivityChart(userData.activity_trend);
        renderRoleUsageChart(userData.role_usage);
        renderTopUsersTable(userData.top_users);
        
        // Security (merged in)
        renderLoginPatternChart(securityData.hourly_pattern);
        renderFailedLogins(securityData.failed_logins);
        renderLoginSummaryTable(securityData.user_summary);
        
        hideLoading();
    } catch (error) {
        console.error('Error loading users & security:', error);
        hideLoading();
    }
}

// Keep old function name for backwards compatibility
async function loadUsers() {
    return loadUsersAndSecurity();
}

function renderUserActivityChart(data) {
    const ctx = document.getElementById('userActivityChart').getContext('2d');
    
    if (state.charts.userActivity) {
        state.charts.userActivity.destroy();
    }
    
    state.charts.userActivity = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.DATE),
            datasets: [
                {
                    label: 'Active Users',
                    data: data.map(d => d.ACTIVE_USERS),
                    borderColor: chartColors.cyan,
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    fill: true,
                    yAxisID: 'y'
                },
                {
                    label: 'Total Queries',
                    data: data.map(d => d.TOTAL_QUERIES),
                    borderColor: chartColors.purple,
                    backgroundColor: 'transparent',
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { type: 'linear', position: 'left', title: { display: true, text: 'Users' } },
                y1: { type: 'linear', position: 'right', title: { display: true, text: 'Queries' }, grid: { drawOnChartArea: false } }
            }
        }
    });
}

function renderRoleUsageChart(data) {
    const ctx = document.getElementById('roleUsageChart').getContext('2d');
    
    if (state.charts.roleUsage) {
        state.charts.roleUsage.destroy();
    }
    
    state.charts.roleUsage = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(d => d.ROLE_NAME),
            datasets: [{
                data: data.map(d => d.QUERY_COUNT),
                backgroundColor: chartColorPalette
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right' }
            }
        }
    });
}

function renderTopUsersTable(data) {
    const tbody = document.querySelector('#topUsersTable tbody');
    tbody.innerHTML = data.map(row => `
        <tr>
            <td><strong>${row.USER_NAME}</strong></td>
            <td>${formatNumber(row.QUERY_COUNT, 0)} <span class="unit">queries</span></td>
            <td>${formatNumber(row.TOTAL_HOURS, 1)} <span class="unit">hrs</span></td>
            <td>${formatNumber(row.AVG_QUERY_SEC, 1)} <span class="unit">sec</span></td>
            <td>${formatNumber(row.TB_SCANNED, 2)} <span class="unit">TB</span></td>
            <td>${formatNumber(row.FAILED_QUERIES, 0)}</td>
            <td>${row.WAREHOUSES_USED}</td>
        </tr>
    `).join('');
}

// ============================================
// NEW FEATURE: Optimization
// ============================================

async function loadOptimization() {
    showLoading('Analyzing query patterns...');
    try {
        const [fingerprints, opportunities] = await Promise.all([
            fetchAPI('query-fingerprints', { days: 7 }),
            fetchAPI('optimization-opportunities')
        ]);
        
        renderFingerprintsTable(fingerprints);
        renderOptimizationTable(opportunities);
        
        hideLoading();
    } catch (error) {
        console.error('Error loading optimization:', error);
        hideLoading();
    }
}

function renderFingerprintsTable(data) {
    const tbody = document.querySelector('#fingerprintsTable tbody');
    tbody.innerHTML = data.map(row => `
        <tr>
            <td><code class="query-pattern">${truncateText(row.SAMPLE_QUERY, 60)}</code></td>
            <td>${formatNumber(row.EXECUTION_COUNT, 0)} <span class="unit">times</span></td>
            <td>${formatNumber(row.AVG_DURATION_SEC, 1)} <span class="unit">sec</span></td>
            <td>${formatNumber(row.TOTAL_HOURS, 1)} <span class="unit">hrs</span></td>
            <td>${formatNumber(row.TOTAL_GB_SCANNED, 1)} <span class="unit">GB</span></td>
            <td>${row.UNIQUE_USERS}</td>
        </tr>
    `).join('');
}

function renderOptimizationTable(data) {
    const tbody = document.querySelector('#optimizationTable tbody');
    tbody.innerHTML = data.map(row => `
        <tr>
            <td><span class="query-id">${truncateText(row.QUERY_ID, 15)}</span></td>
            <td><span class="issue-badge ${row.ISSUE_TYPE.toLowerCase().replace(/\s+/g, '-')}">${row.ISSUE_TYPE}</span></td>
            <td>${row.USER_NAME || '--'}</td>
            <td>${row.WAREHOUSE_NAME || '--'}</td>
            <td>${formatNumber(row.ELAPSED_SEC, 1)} <span class="unit">sec</span></td>
            <td class="recommendation-cell">${row.RECOMMENDATION}</td>
        </tr>
    `).join('');
}

// ============================================
// NEW FEATURE: Storage & Data Freshness
// ============================================

async function loadStorage() {
    showLoading('Loading storage data...');
    try {
        const [tableStorage, freshness, unused] = await Promise.all([
            fetchAPI('table-storage'),
            fetchAPI('data-freshness'),
            fetchAPI('unused-objects', { days: 30 })
        ]);
        
        renderTableStorageTable(tableStorage);
        renderFreshnessTable(freshness);
        renderUnusedObjects(unused);
        
        hideLoading();
    } catch (error) {
        console.error('Error loading storage:', error);
        hideLoading();
    }
}

function renderTableStorageTable(data) {
    const tbody = document.querySelector('#tableStorageTable tbody');
    tbody.innerHTML = data.slice(0, 30).map(row => `
        <tr>
            <td>${row.DATABASE_NAME}</td>
            <td>${row.SCHEMA_NAME}</td>
            <td><strong>${row.TABLE_NAME}</strong></td>
            <td>${formatNumber(row.ROW_COUNT, 0)}</td>
            <td>${formatNumber(row.SIZE_GB, 2)} <span class="unit">GB</span></td>
            <td>${formatNumber(row.ACTIVE_GB, 2)} <span class="unit">GB</span></td>
            <td>${formatNumber(row.TIME_TRAVEL_GB, 2)} <span class="unit">GB</span></td>
            <td>${formatNumber(row.FAILSAFE_GB, 2)} <span class="unit">GB</span></td>
            <td><code>${row.CLUSTERING_KEY || 'None'}</code></td>
        </tr>
    `).join('');
}

function renderFreshnessTable(data) {
    const tbody = document.querySelector('#freshnessTable tbody');
    tbody.innerHTML = data.slice(0, 30).map(row => `
        <tr>
            <td>${row.DATABASE_NAME}</td>
            <td>${row.SCHEMA_NAME}</td>
            <td><strong>${row.TABLE_NAME}</strong></td>
            <td>${formatNumber(row.ROW_COUNT, 0)}</td>
            <td>${formatNumber(row.SIZE_GB, 2)} <span class="unit">GB</span></td>
            <td>${formatDate(row.LAST_ALTERED)}</td>
            <td>${formatNumber(row.HOURS_SINCE_UPDATE, 0)} <span class="unit">hrs</span></td>
            <td><span class="freshness-badge ${row.FRESHNESS_STATUS.toLowerCase().replace(' ', '-')}">${row.FRESHNESS_STATUS}</span></td>
        </tr>
    `).join('');
}

function renderUnusedObjects(data) {
    const container = document.getElementById('unusedObjectsGrid');
    
    let html = '<div class="unused-section">';
    html += '<h4>Unused Warehouses</h4>';
    if (data.unused_warehouses && data.unused_warehouses.length > 0) {
        html += '<ul class="unused-list">';
        data.unused_warehouses.forEach(wh => {
            html += `<li><strong>${wh.WAREHOUSE_NAME}</strong> (${wh.SIZE})</li>`;
        });
        html += '</ul>';
    } else {
        html += '<p class="no-data">No unused warehouses found</p>';
    }
    html += '</div>';
    
    html += '<div class="unused-section">';
    html += '<h4>Unused Tables (>1GB, >30 days)</h4>';
    if (data.unused_tables && data.unused_tables.length > 0) {
        html += '<ul class="unused-list">';
        data.unused_tables.slice(0, 10).forEach(tbl => {
            html += `<li><strong>${tbl.DATABASE_NAME}.${tbl.SCHEMA_NAME}.${tbl.TABLE_NAME}</strong> - ${formatNumber(tbl.SIZE_GB, 1)} GB, ${tbl.DAYS_SINCE_ALTERED} days old</li>`;
        });
        html += '</ul>';
    } else {
        html += '<p class="no-data">No unused tables found</p>';
    }
    html += '</div>';
    
    container.innerHTML = html;
}

// ============================================
// NEW FEATURE: Security
// ============================================

async function loadSecurity() {
    showLoading('Loading security data...');
    try {
        const data = await fetchAPI('login-history', { days: 7 });
        
        renderLoginPatternChart(data.hourly_pattern);
        renderFailedLogins(data.failed_logins);
        renderLoginSummaryTable(data.summary);
        
        hideLoading();
    } catch (error) {
        console.error('Error loading security:', error);
        hideLoading();
    }
}

function renderLoginPatternChart(data) {
    const ctx = document.getElementById('loginPatternChart').getContext('2d');
    
    if (state.charts.loginPattern) {
        state.charts.loginPattern.destroy();
    }
    
    state.charts.loginPattern = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => `${d.HOUR_OF_DAY}:00`),
            datasets: [{
                label: 'Login Count',
                data: data.map(d => d.LOGIN_COUNT),
                backgroundColor: chartColors.cyan,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function renderFailedLogins(data) {
    const container = document.getElementById('failedLoginsList');
    
    if (!data || data.length === 0) {
        container.innerHTML = '<p class="no-data">No failed login attempts in the last 7 days</p>';
        return;
    }
    
    container.innerHTML = data.slice(0, 10).map(login => `
        <div class="failed-login-item">
            <div class="login-info">
                <strong>${login.USER_NAME}</strong>
                <span class="ip">${login.CLIENT_IP}</span>
            </div>
            <div class="login-details">
                <span class="time">${formatDate(login.EVENT_TIMESTAMP)}</span>
                <span class="error">${login.ERROR_MESSAGE || 'Unknown error'}</span>
            </div>
        </div>
    `).join('');
}

function renderLoginSummaryTable(data) {
    const tbody = document.querySelector('#loginSummaryTable tbody');
    tbody.innerHTML = data.map(row => `
        <tr>
            <td><strong>${row.USER_NAME}</strong></td>
            <td>${row.LOGIN_COUNT}</td>
            <td>${row.UNIQUE_IPS}</td>
            <td>${formatDate(row.LAST_LOGIN)}</td>
            <td><span class="${row.FAILED_LOGINS > 0 ? 'alert-text' : ''}">${row.FAILED_LOGINS}</span></td>
        </tr>
    `).join('');
}

// ============================================
// DATABASE DEEP DIVE
// ============================================

// Store selected database
let selectedDatabase = null;

async function loadDatabaseList() {
    try {
        const databases = await fetchAPI('databases');
        const select = document.getElementById('databaseSelect');
        
        select.innerHTML = '<option value="">-- Select a Database --</option>' +
            databases.map(db => `<option value="${db.DATABASE_NAME}">${db.DATABASE_NAME}</option>`).join('');
        
    } catch (error) {
        console.error('Error loading database list:', error);
    }
}

async function loadDatabaseAnalysis() {
    const dbName = document.getElementById('databaseSelect').value;
    const days = document.getElementById('dbDaysFilter').value;
    
    if (!dbName) {
        showToast('Please select a database', 'error');
        return;
    }
    
    selectedDatabase = dbName;
    showLoading(`Analyzing database: ${dbName}...`);
    
    try {
        // Load all data in parallel
        const [overview, costAnalysis, slowQueries, bottlenecks, tables, patterns, optimization, recommendations] = await Promise.all([
            fetchAPI(`database/${dbName}/overview`, { days }),
            fetchAPI(`database/${dbName}/cost-analysis`, { days }),
            fetchAPI(`database/${dbName}/slow-queries`, { days: 7, threshold: 30 }),
            fetchAPI(`database/${dbName}/bottlenecks`, { days: 7 }),
            fetchAPI(`database/${dbName}/tables`),
            fetchAPI(`database/${dbName}/query-patterns`, { days: 7 }),
            fetchAPI(`database/${dbName}/optimization`, { days: 7 }),
            fetchAPI(`database/${dbName}/recommendations`, { days })
        ]);
        
        // Show the overview section, hide empty state
        document.getElementById('dbOverviewSection').style.display = 'block';
        document.getElementById('dbEmptyState').style.display = 'none';
        document.getElementById('selectedDbName').textContent = dbName;
        
        // Update overview metrics
        const qm = overview.query_metrics || {};
        const st = overview.storage || {};
        const ob = overview.objects || {};
        
        document.getElementById('dbTotalQueries').textContent = formatNumber(qm.TOTAL_QUERIES, 0);
        document.getElementById('dbActiveUsers').textContent = qm.UNIQUE_USERS || '--';
        document.getElementById('dbAvgQueryTime').textContent = formatNumber(qm.AVG_QUERY_SEC, 1);
        document.getElementById('dbTbScanned').textContent = formatNumber(qm.TB_SCANNED, 2);
        document.getElementById('dbFailedQueries').textContent = formatNumber(qm.FAILED_QUERIES, 0);
        
        // Storage with smart units and breakdown
        const totalGb = st.TOTAL_GB || 0;
        const dbGb = st.DATABASE_GB || 0;
        const failsafeGb = st.FAILSAFE_GB || 0;
        
        if (totalGb >= 1024) {
            document.getElementById('dbStorage').textContent = formatNumber(totalGb / 1024, 2);
            document.getElementById('dbStorageUnit').textContent = 'TB';
        } else {
            document.getElementById('dbStorage').textContent = formatNumber(totalGb, 1);
            document.getElementById('dbStorageUnit').textContent = 'GB';
        }
        
        // Storage breakdown
        document.getElementById('dbStorageDb').textContent = formatStorageSize(dbGb);
        document.getElementById('dbStorageFailsafe').textContent = formatStorageSize(failsafeGb);
        
        // Render all tabs
        renderDbCostTab(costAnalysis);
        renderDbPerformanceTab(patterns, slowQueries);
        renderDbBottlenecksTab(bottlenecks, optimization);
        renderDbTablesTab(tables, patterns.by_schema);
        renderDbRecommendations(recommendations);
        
        hideLoading();
        showToast(`Loaded analysis for ${dbName}`);
        
    } catch (error) {
        console.error('Error loading database analysis:', error);
        hideLoading();
    }
}

function renderDbCostTab(costAnalysis) {
    // Daily volume chart
    const dailyCtx = document.getElementById('dbDailyVolumeChart').getContext('2d');
    if (state.charts.dbDailyVolume) state.charts.dbDailyVolume.destroy();
    
    state.charts.dbDailyVolume = new Chart(dailyCtx, {
        type: 'line',
        data: {
            labels: costAnalysis.daily_volume.map(d => d.DATE),
            datasets: [
                {
                    label: 'Queries',
                    data: costAnalysis.daily_volume.map(d => d.QUERY_COUNT),
                    borderColor: chartColors.cyan,
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    fill: true,
                    yAxisID: 'y'
                },
                {
                    label: 'Compute Hours',
                    data: costAnalysis.daily_volume.map(d => d.TOTAL_HOURS),
                    borderColor: chartColors.orange,
                    backgroundColor: 'transparent',
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { type: 'linear', position: 'left', title: { display: true, text: 'Queries' } },
                y1: { type: 'linear', position: 'right', title: { display: true, text: 'Hours' }, grid: { drawOnChartArea: false } }
            }
        }
    });
    
    // Warehouse chart - show hours with credits/hour rate
    const whCtx = document.getElementById('dbWarehouseChart').getContext('2d');
    if (state.charts.dbWarehouse) state.charts.dbWarehouse.destroy();
    
    // Credit rates by warehouse size
    const creditRates = {
        'X-Small': 1, 'Small': 2, 'Medium': 4, 'Large': 8,
        'X-Large': 16, '2X-Large': 32, '3X-Large': 64, '4X-Large': 128
    };
    
    state.charts.dbWarehouse = new Chart(whCtx, {
        type: 'bar',
        data: {
            labels: costAnalysis.by_warehouse.map(d => {
                const rate = creditRates[d.WAREHOUSE_SIZE] || '?';
                return `${d.WAREHOUSE_NAME} (${d.WAREHOUSE_SIZE} = ${rate} cr/hr)`;
            }),
            datasets: [{
                label: 'Compute Hours',
                data: costAnalysis.by_warehouse.map(d => d.TOTAL_HOURS),
                backgroundColor: chartColorPalette
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                tooltip: {
                    callbacks: {
                        afterLabel: function(context) {
                            const data = costAnalysis.by_warehouse[context.dataIndex];
                            const rate = creditRates[data.WAREHOUSE_SIZE] || 4;
                            const estCredits = data.TOTAL_HOURS * rate;
                            return `≈ ${formatNumber(estCredits, 0)} credits\nQueries: ${formatNumber(data.QUERY_COUNT, 0)}\nTB Scanned: ${formatNumber(data.TB_SCANNED, 2)}`;
                        }
                    }
                }
            },
            scales: {
                x: { title: { display: true, text: 'Hours' } }
            }
        }
    });
    
    // User cost table
    const tbody = document.querySelector('#dbUserCostTable tbody');
    tbody.innerHTML = costAnalysis.by_user.map(row => `
        <tr>
            <td><strong>${row.USER_NAME}</strong></td>
            <td>${formatNumber(row.QUERY_COUNT, 0)} <span class="unit">queries</span></td>
            <td>${formatNumber(row.TOTAL_HOURS, 1)} <span class="unit">hrs</span></td>
            <td>${formatNumber(row.AVG_QUERY_SEC, 1)} <span class="unit">sec</span></td>
            <td>${formatNumber(row.TB_SCANNED, 2)} <span class="unit">TB</span></td>
        </tr>
    `).join('');
}

function renderDbPerformanceTab(patterns, slowQueries) {
    // Hourly chart
    const hourlyCtx = document.getElementById('dbHourlyChart').getContext('2d');
    if (state.charts.dbHourly) state.charts.dbHourly.destroy();
    
    state.charts.dbHourly = new Chart(hourlyCtx, {
        type: 'bar',
        data: {
            labels: patterns.hourly.map(d => `${d.HOUR_OF_DAY}:00`),
            datasets: [{
                label: 'Query Count',
                data: patterns.hourly.map(d => d.QUERY_COUNT),
                backgroundColor: chartColors.cyan,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
    
    // Query type chart
    const typeCtx = document.getElementById('dbQueryTypeChart').getContext('2d');
    if (state.charts.dbQueryType) state.charts.dbQueryType.destroy();
    
    state.charts.dbQueryType = new Chart(typeCtx, {
        type: 'doughnut',
        data: {
            labels: patterns.by_type.map(d => d.QUERY_TYPE),
            datasets: [{
                data: patterns.by_type.map(d => d.QUERY_COUNT),
                backgroundColor: chartColorPalette
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'right' } }
        }
    });
    
    // Slow queries table - clickable query IDs
    const tbody = document.querySelector('#dbSlowQueriesTable tbody');
    tbody.innerHTML = slowQueries.slice(0, 30).map(row => `
        <tr>
            <td><span class="query-id clickable-query" data-query="${encodeURIComponent(row.QUERY_TEXT || '')}">${truncateText(row.QUERY_ID, 15)}</span></td>
            <td>${row.USER_NAME || '--'}</td>
            <td>${row.WAREHOUSE_NAME || '--'}</td>
            <td>${row.QUERY_TYPE || '--'}</td>
            <td>${formatNumber(row.ELAPSED_SEC, 1)} <span class="unit">sec</span></td>
            <td>${formatNumber(row.GB_SCANNED, 2)} <span class="unit">GB</span></td>
            <td>${formatNumber(row.QUEUE_SEC, 1)} <span class="unit">sec</span></td>
            <td><span class="status-badge ${(row.EXECUTION_STATUS || '').toLowerCase()}">${row.EXECUTION_STATUS || '--'}</span></td>
        </tr>
    `).join('');
    
    // Attach click handlers for query IDs
    attachQueryIdListeners();
}

function renderDbBottlenecksTab(bottlenecks, optimization) {
    // Queue issues - show summary AND list of queued queries
    let queueHtml = '';
    if (bottlenecks.queuing.length > 0) {
        queueHtml = bottlenecks.queuing.map(item => `
            <div class="bottleneck-item">
                <span class="label">${item.WAREHOUSE_NAME}</span>
                <span class="value ${item.AVG_QUEUE_SEC > 10 ? 'danger' : (item.AVG_QUEUE_SEC > 5 ? 'warning' : '')}">${formatNumber(item.QUEUED_QUERIES, 0)} queued, avg ${formatNumber(item.AVG_QUEUE_SEC, 1)}s</span>
            </div>
        `).join('');
        
        // Add clickable queued queries list
        if (bottlenecks.queued_queries && bottlenecks.queued_queries.length > 0) {
            queueHtml += '<div class="bottleneck-queries-list"><h5>Top Queued Queries:</h5>';
            queueHtml += bottlenecks.queued_queries.slice(0, 5).map(q => `
                <div class="query-row clickable-query" data-query="${encodeURIComponent(q.QUERY_TEXT || '')}">
                    <span class="query-id-link">${truncateText(q.QUERY_ID, 20)}</span>
                    <span class="queue-time">${formatNumber(q.QUEUE_SEC, 1)}s queue</span>
                </div>
            `).join('');
            queueHtml += '</div>';
        }
    } else {
        queueHtml = '<p class="no-data">No significant queue issues</p>';
    }
    document.getElementById('dbQueueIssues').innerHTML = queueHtml;
    
    // Spill issues
    const spillHtml = bottlenecks.spilling.length > 0 ? bottlenecks.spilling.map(item => `
        <div class="bottleneck-item">
            <span class="label">${item.WAREHOUSE_NAME}</span>
            <span class="value ${item.REMOTE_SPILL_GB > 5 ? 'danger' : 'warning'}">${formatNumber(item.LOCAL_SPILL_GB, 1)} <span class="unit">GB</span> local, ${formatNumber(item.REMOTE_SPILL_GB, 1)} <span class="unit">GB</span> remote</span>
        </div>
    `).join('') : '<p class="no-data">No significant spilling</p>';
    document.getElementById('dbSpillIssues').innerHTML = spillHtml;
    
    // Full scan issues - show summary AND detailed list with suggested columns
    const scanData = bottlenecks.full_scans[0] || {};
    let scanHtml = '';
    
    if (scanData.FULL_SCAN_COUNT > 0) {
        scanHtml = `
            <div class="bottleneck-item">
                <span class="label">Full Table Scans</span>
                <span class="value ${scanData.FULL_SCAN_COUNT > 100 ? 'danger' : 'warning'}">${formatNumber(scanData.FULL_SCAN_COUNT, 0)} queries</span>
            </div>
            <div class="bottleneck-item">
                <span class="label">Total Data Scanned</span>
                <span class="value">${formatNumber(scanData.TOTAL_TB_SCANNED, 2)} <span class="unit">TB</span></span>
            </div>
        `;
        
        // Add detailed full scan list with suggested clustering columns
        if (bottlenecks.full_scan_details && bottlenecks.full_scan_details.length > 0) {
            scanHtml += '<div class="bottleneck-queries-list"><h5>Tables to Cluster:</h5>';
            scanHtml += bottlenecks.full_scan_details.slice(0, 5).map(scan => `
                <div class="scan-suggestion clickable-query" data-query="${encodeURIComponent(scan.QUERY_TEXT || '')}">
                    <div class="scan-table"><strong>${scan.TABLE_NAME || 'Unknown'}</strong> - ${formatNumber(scan.GB_SCANNED, 1)} GB scanned</div>
                    <div class="scan-columns">Cluster on: <code>${scan.SUGGESTED_COLUMNS || 'date/timestamp columns'}</code></div>
                </div>
            `).join('');
            scanHtml += '</div>';
        }
        
        // Add unclustered tables recommendation
        if (bottlenecks.unclustered_tables && bottlenecks.unclustered_tables.length > 0) {
            scanHtml += '<div class="unclustered-alert"><h5>⚠️ Large Tables Without Clustering:</h5>';
            scanHtml += bottlenecks.unclustered_tables.slice(0, 3).map(t => `
                <div class="unclustered-table">${t.TABLE_SCHEMA}.${t.TABLE_NAME} (${formatNumber(t.SIZE_GB, 1)} GB)</div>
            `).join('');
            scanHtml += '</div>';
        }
    } else {
        scanHtml = '<p class="no-data">No significant full table scans</p>';
    }
    document.getElementById('dbScanIssues').innerHTML = scanHtml;
    
    // Failure issues
    const failHtml = bottlenecks.failures.length > 0 ? bottlenecks.failures.slice(0, 3).map(item => `
        <div class="bottleneck-item">
            <span class="label">${truncateText(item.ERROR_MESSAGE, 40)}</span>
            <span class="value danger">${item.FAILURE_COUNT} failures</span>
        </div>
    `).join('') : '<p class="no-data">No query failures</p>';
    document.getElementById('dbFailureIssues').innerHTML = failHtml;
    
    // Optimization table
    const tbody = document.querySelector('#dbOptimizationTable tbody');
    tbody.innerHTML = optimization.slice(0, 20).map(row => `
        <tr>
            <td><span class="query-id clickable-query" data-query="${encodeURIComponent(row.QUERY_TEXT || '')}">${truncateText(row.QUERY_ID, 15)}</span></td>
            <td><span class="issue-badge ${row.ISSUE_TYPE.toLowerCase().replace(/\s+/g, '-')}">${row.ISSUE_TYPE}</span></td>
            <td>${row.USER_NAME || '--'}</td>
            <td>${row.WAREHOUSE_NAME || '--'}</td>
            <td>${formatNumber(row.ELAPSED_SEC, 1)} <span class="unit">sec</span></td>
            <td class="recommendation-cell">
                ${row.TABLE_NAME ? `<strong>${row.TABLE_NAME}:</strong> ` : ''}${row.RECOMMENDATION}
            </td>
        </tr>
    `).join('');
    
    // Attach click handlers for all query elements
    attachQueryIdListeners();
}

function renderDbTablesTab(tables, bySchema) {
    // Schema chart
    const schemaCtx = document.getElementById('dbSchemaChart').getContext('2d');
    if (state.charts.dbSchema) state.charts.dbSchema.destroy();
    
    state.charts.dbSchema = new Chart(schemaCtx, {
        type: 'bar',
        data: {
            labels: bySchema.map(d => d.SCHEMA_NAME),
            datasets: [{
                label: 'Query Count',
                data: bySchema.map(d => d.QUERY_COUNT),
                backgroundColor: chartColorPalette
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y'
        }
    });
    
    // Table size chart (top 10)
    const topTables = tables.slice(0, 10);
    const sizeCtx = document.getElementById('dbTableSizeChart').getContext('2d');
    if (state.charts.dbTableSize) state.charts.dbTableSize.destroy();
    
    state.charts.dbTableSize = new Chart(sizeCtx, {
        type: 'bar',
        data: {
            labels: topTables.map(d => d.TABLE_NAME),
            datasets: [{
                label: 'Size (GB)',
                data: topTables.map(d => d.SIZE_GB),
                backgroundColor: chartColors.cyan
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y'
        }
    });
    
    // Tables table
    const tbody = document.querySelector('#dbTablesTable tbody');
    tbody.innerHTML = tables.slice(0, 30).map(row => `
        <tr>
            <td>${row.TABLE_SCHEMA}</td>
            <td><strong>${row.TABLE_NAME}</strong></td>
            <td>${formatNumber(row.ROW_COUNT, 0)}</td>
            <td>${formatNumber(row.SIZE_GB, 2)} <span class="unit">GB</span></td>
            <td><code>${row.CLUSTERING_KEY || 'None'}</code></td>
            <td>${formatDate(row.LAST_ALTERED)}</td>
            <td><span class="freshness-badge ${row.FRESHNESS.toLowerCase().replace(' ', '-')}">${row.FRESHNESS}</span></td>
        </tr>
    `).join('');
}

function renderDbRecommendations(recommendations) {
    const container = document.getElementById('dbRecommendationsContainer');
    
    if (!recommendations || recommendations.length === 0) {
        container.innerHTML = '<p class="no-data">No recommendations - this database is performing well!</p>';
        return;
    }
    
    container.innerHTML = recommendations.map(rec => `
        <div class="db-recommendation-card ${rec.severity.toLowerCase()}">
            <div class="db-recommendation-header">
                <h4>${rec.title}</h4>
                <span class="category">${rec.category}</span>
            </div>
            <p>${rec.description}</p>
            <span class="metric">${rec.metric}</span>
        </div>
    `).join('');
}

// ============================================
// Query ID Click Handler - Show Full SQL
// ============================================

function attachQueryIdListeners() {
    // Attach click handlers to all clickable query elements
    document.querySelectorAll('.clickable-query, .query-id[data-query]').forEach(el => {
        el.style.cursor = 'pointer';
        el.addEventListener('click', function(e) {
            e.preventDefault();
            const queryText = decodeURIComponent(this.dataset.query || '');
            if (queryText) {
                showQueryModal(queryText);
            }
        });
    });
}

function showQueryModal(queryText) {
    // Use existing modal if available, otherwise create one
    let modal = document.getElementById('queryModal');
    
    if (!modal) {
        // Create modal dynamically
        modal = document.createElement('div');
        modal.id = 'queryModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Query Details</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <pre class="query-text-display"></pre>
                </div>
                <div class="modal-footer">
                    <button class="btn-copy" onclick="copyQueryToClipboard()">Copy to Clipboard</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Add close handler
        modal.querySelector('.modal-close').addEventListener('click', () => {
            modal.classList.remove('active');
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.classList.remove('active');
        });
    }
    
    // Update query text and show modal
    const queryDisplay = modal.querySelector('.query-text-display') || modal.querySelector('#queryText');
    if (queryDisplay) {
        queryDisplay.textContent = queryText;
    }
    modal.classList.add('active');
}

function copyQueryToClipboard() {
    const modal = document.getElementById('queryModal');
    const queryText = modal.querySelector('.query-text-display, #queryText').textContent;
    navigator.clipboard.writeText(queryText).then(() => {
        showToast('Query copied to clipboard');
    });
}

// ============================================
// Initialization
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadOverview();
    document.getElementById('lastRefresh').textContent = new Date().toLocaleTimeString();
});
