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
// API Functions
// ============================================

async function fetchAPI(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `/api/${endpoint}?${queryString}` : `/api/${endpoint}`;
    
    try {
        const response = await fetch(url);
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
        
    } catch (error) {
        console.error('Error loading overview:', error);
    }
}

async function loadCosts() {
    const days = document.getElementById('costDaysFilter').value;
    
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
        
    } catch (error) {
        console.error('Error loading costs:', error);
    }
}

async function loadQueries() {
    const threshold = document.getElementById('queryThreshold').value;
    const limit = document.getElementById('queryLimit').value;
    
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
        
    } catch (error) {
        console.error('Error loading queries:', error);
    }
}

async function loadWarehouses() {
    try {
        const [configs, clusterLoad] = await Promise.all([
            fetchAPI('warehouse-config'),
            fetchAPI('cluster-load', { days: 7 })
        ]);
        
        renderWarehouseConfigTable(configs);
        renderClusterLoadChart(clusterLoad);
        
    } catch (error) {
        console.error('Error loading warehouses:', error);
    }
}

async function loadBottlenecks() {
    try {
        const [bottlenecks, patterns] = await Promise.all([
            fetchAPI('bottleneck-analysis'),
            fetchAPI('query-patterns', { days: 7 })
        ]);
        
        renderBottleneckCards(bottlenecks);
        renderQueryPatternChart(patterns.hourly);
        renderQueryTypeChart(patterns.by_type);
        
    } catch (error) {
        console.error('Error loading bottlenecks:', error);
    }
}

async function loadRecommendations() {
    try {
        const recommendations = await fetchAPI('recommendations');
        renderRecommendations(recommendations);
    } catch (error) {
        console.error('Error loading recommendations:', error);
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
            <td>${formatNumber(row.TOTAL_CREDITS)}</td>
            <td>${formatNumber(row.COMPUTE_CREDITS)}</td>
            <td>${formatNumber(row.CLOUD_SERVICES_CREDITS)}</td>
            <td>${row.ACTIVE_DAYS}</td>
            <td>${formatNumber(row.AVG_HOURLY_CREDITS, 3)}</td>
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
            <td>${formatNumber(row.ELAPSED_SECONDS, 1)}</td>
            <td>${formatNumber(row.GB_SCANNED, 2)}</td>
            <td>${formatNumber((row.QUEUED_OVERLOAD_SECONDS || 0) + (row.QUEUED_PROVISIONING_SECONDS || 0), 1)}</td>
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
            <td>${formatNumber(row.ELAPSED_SECONDS, 1)}</td>
            <td>${formatNumber(row.GB_SCANNED, 2)}</td>
            <td>${formatNumber(row.GB_WRITTEN, 2)}</td>
            <td>${formatNumber(row.ROWS_PRODUCED, 0)}</td>
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
            <td>${formatNumber(row.TOTAL_SEC, 1)}</td>
            <td>${formatNumber(row.QUEUE_SEC, 1)}</td>
            <td>${formatNumber(row.PROVISIONING_SEC, 1)}</td>
            <td>${formatNumber(row.EXECUTION_SEC, 1)}</td>
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
            <td>${row.AUTO_SUSPEND || '--'}</td>
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
        case 'costs':
            loadCosts();
            break;
        case 'queries':
            loadQueries();
            break;
        case 'warehouses':
            loadWarehouses();
            break;
        case 'bottlenecks':
            loadBottlenecks();
            break;
        case 'recommendations':
            loadRecommendations();
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
}

// ============================================
// Initialization
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadOverview();
    document.getElementById('lastRefresh').textContent = new Date().toLocaleTimeString();
});
