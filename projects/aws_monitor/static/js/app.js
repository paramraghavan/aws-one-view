/* ============================================================================
   AWS Resource Monitor - Frontend Application
   Clean, maintainable JavaScript organized by feature
   ============================================================================ */

// ----------------------------------------------------------------------------
// GLOBAL STATE
// ----------------------------------------------------------------------------
let selectedResources = [];
let currentResourceType = 'ec2';
let allResources = null;
let metricsChart = null;
let costChart = null;

// ----------------------------------------------------------------------------
// INITIALIZATION
// ----------------------------------------------------------------------------
$(document).ready(function() {
    initializeApp();
    setupEventHandlers();
});

function initializeApp() {
    console.log('Initializing AWS Resource Monitor...');
    loadRegions();
    loadMonitoringStatus();
}

// ----------------------------------------------------------------------------
// EVENT HANDLERS
// ----------------------------------------------------------------------------
function setupEventHandlers() {
    // Load resources button
    $('#loadResources').click(loadResources);
    
    // Resource type tabs
    $('.tab-btn').click(function() {
        $('.tab-btn').removeClass('active');
        $(this).addClass('active');
        currentResourceType = $(this).data('type');
        displayResources();
    });
    
    // Load metrics button
    $('#loadMetrics').click(loadMetrics);
    
    // Load costs button
    $('#loadCosts').click(loadCosts);
    
    // Detect bottlenecks button
    $('#detectBottlenecks').click(detectBottlenecks);
    
    // Monitoring controls
    $('#startMonitoring').click(startMonitoring);
    $('#stopMonitoring').click(stopMonitoring);
    $('#addToMonitoring').click(addSelectedToMonitoring);
    $('#testAlert').click(sendTestAlert);
}

// ----------------------------------------------------------------------------
// REGION MANAGEMENT
// ----------------------------------------------------------------------------
function loadRegions() {
    $.ajax({
        url: '/api/regions',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                displayRegions(response.data);
            } else {
                showError('Failed to load regions');
            }
        },
        error: function() {
            showError('Error connecting to server');
        }
    });
}

function displayRegions(regions) {
    const container = $('#regionSelector');
    container.empty();
    
    // Pre-select common regions
    const defaultRegions = ['us-east-1', 'us-west-2'];
    
    regions.forEach(region => {
        const checked = defaultRegions.includes(region) ? 'checked' : '';
        const html = `
            <div class="region-item">
                <input type="checkbox" id="region-${region}" value="${region}" ${checked}>
                <label for="region-${region}">${region}</label>
            </div>
        `;
        container.append(html);
    });
}

function getSelectedRegions() {
    const selected = [];
    $('#regionSelector input:checked').each(function() {
        selected.push($(this).val());
    });
    return selected.length > 0 ? selected : ['us-east-1'];
}

// ----------------------------------------------------------------------------
// RESOURCE MANAGEMENT
// ----------------------------------------------------------------------------
function loadResources() {
    const regions = getSelectedRegions();
    
    if (regions.length === 0) {
        alert('Please select at least one region');
        return;
    }
    
    $('#resourceList').html('<div class="loading">Loading resources</div>');
    
    $.ajax({
        url: '/api/resources',
        method: 'GET',
        data: { regions: regions },
        traditional: true,
        success: function(response) {
            if (response.success) {
                allResources = response.data;
                displayResources();
            } else {
                showError('Failed to load resources: ' + response.error);
            }
        },
        error: function(xhr) {
            showError('Error loading resources');
        }
    });
}

function displayResources() {
    if (!allResources) {
        return;
    }
    
    const resources = allResources[currentResourceType] || [];
    const container = $('#resourceList');
    container.empty();
    
    if (resources.length === 0) {
        container.html('<p class="info-text">No ' + currentResourceType.toUpperCase() + ' resources found</p>');
        return;
    }
    
    // Build table based on resource type
    let table = '<table class="resource-table"><thead><tr>';
    
    // Define columns for each resource type
    const columns = getColumnsForResourceType(currentResourceType);
    table += '<th><input type="checkbox" id="selectAll"></th>';
    columns.forEach(col => table += '<th>' + col + '</th>');
    table += '</tr></thead><tbody>';
    
    // Add rows
    resources.forEach(resource => {
        table += '<tr>';
        table += '<td><input type="checkbox" class="resource-checkbox" data-id="' + resource.id + '" data-region="' + resource.region + '"></td>';
        table += getRowContentForResource(currentResourceType, resource);
        table += '</tr>';
    });
    
    table += '</tbody></table>';
    container.html(table);
    
    // Setup checkbox handlers
    setupResourceCheckboxes();
}

function getColumnsForResourceType(type) {
    const columnMap = {
        'ec2': ['Instance ID', 'Type', 'State', 'Region'],
        'rds': ['DB ID', 'Class', 'Engine', 'Status', 'Region'],
        's3': ['Bucket Name', 'Region', 'Created'],
        'lambda': ['Function Name', 'Runtime', 'Memory (MB)', 'Region'],
        'ebs': ['Volume ID', 'Size (GB)', 'Type', 'State', 'Region']
    };
    return columnMap[type] || [];
}

function getRowContentForResource(type, resource) {
    let html = '';
    
    switch(type) {
        case 'ec2':
            html += '<td>' + resource.id + '</td>';
            html += '<td>' + resource.type + '</td>';
            html += '<td><span class="status-badge status-' + resource.state + '">' + resource.state + '</span></td>';
            html += '<td>' + resource.region + '</td>';
            break;
        
        case 'rds':
            html += '<td>' + resource.id + '</td>';
            html += '<td>' + resource.class + '</td>';
            html += '<td>' + resource.engine + '</td>';
            html += '<td><span class="status-badge status-' + resource.status + '">' + resource.status + '</span></td>';
            html += '<td>' + resource.region + '</td>';
            break;
        
        case 's3':
            html += '<td>' + resource.id + '</td>';
            html += '<td>' + resource.region + '</td>';
            html += '<td>' + new Date(resource.created).toLocaleDateString() + '</td>';
            break;
        
        case 'lambda':
            html += '<td>' + resource.id + '</td>';
            html += '<td>' + resource.runtime + '</td>';
            html += '<td>' + resource.memory_mb + '</td>';
            html += '<td>' + resource.region + '</td>';
            break;
        
        case 'ebs':
            html += '<td>' + resource.id + '</td>';
            html += '<td>' + resource.size_gb + '</td>';
            html += '<td>' + resource.type + '</td>';
            html += '<td><span class="status-badge status-' + resource.state + '">' + resource.state + '</span></td>';
            html += '<td>' + resource.region + '</td>';
            break;
    }
    
    return html;
}

function setupResourceCheckboxes() {
    // Select all checkbox
    $('#selectAll').change(function() {
        $('.resource-checkbox').prop('checked', $(this).is(':checked'));
        updateSelectedResources();
    });
    
    // Individual checkboxes
    $('.resource-checkbox').change(function() {
        updateSelectedResources();
    });
}

function updateSelectedResources() {
    selectedResources = [];
    
    $('.resource-checkbox:checked').each(function() {
        selectedResources.push({
            id: $(this).data('id'),
            region: $(this).data('region'),
            type: currentResourceType
        });
    });
    
    // Show/hide metrics section based on selection
    if (selectedResources.length > 0 && ['ec2', 'rds', 'lambda'].includes(currentResourceType)) {
        $('#metricsSection').show();
        $('#monitoringActions').show();
    } else {
        $('#metricsSection').hide();
        if (selectedResources.length === 0) {
            $('#monitoringActions').hide();
        }
    }
    
    console.log('Selected resources:', selectedResources.length);
}

// ----------------------------------------------------------------------------
// METRICS VISUALIZATION
// ----------------------------------------------------------------------------
function loadMetrics() {
    if (selectedResources.length === 0) {
        alert('Please select resources first');
        return;
    }
    
    const resourceIds = selectedResources.map(r => r.id);
    const region = selectedResources[0].region;
    const hours = parseInt($('#metricHours').val());
    
    $.ajax({
        url: '/api/metrics',
        method: 'GET',
        data: {
            resource_ids: resourceIds,
            resource_type: currentResourceType,
            region: region,
            hours: hours
        },
        traditional: true,
        success: function(response) {
            if (response.success) {
                displayMetrics(response.data);
            } else {
                showError('Failed to load metrics');
            }
        },
        error: function() {
            showError('Error loading metrics');
        }
    });
}

function displayMetrics(metricsData) {
    const ctx = document.getElementById('metricsChart');
    
    // Destroy existing chart
    if (metricsChart) {
        metricsChart.destroy();
    }
    
    // Prepare datasets
    const datasets = [];
    const colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a'];
    let colorIndex = 0;
    
    Object.entries(metricsData).forEach(([resourceId, metrics]) => {
        if (metrics.cpu && metrics.cpu.length > 0) {
            datasets.push({
                label: resourceId + ' CPU',
                data: metrics.cpu.map(dp => ({
                    x: new Date(dp.Timestamp),
                    y: dp.Average
                })),
                borderColor: colors[colorIndex % colors.length],
                backgroundColor: colors[colorIndex % colors.length] + '33',
                tension: 0.4
            });
            colorIndex++;
        }
    });
    
    // Create chart
    metricsChart = new Chart(ctx, {
        type: 'line',
        data: { datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'hour'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'CPU Utilization (%)'
                    }
                }
            }
        }
    });
}

// ----------------------------------------------------------------------------
// COST ANALYSIS
// ----------------------------------------------------------------------------
function loadCosts() {
    const days = parseInt($('#costDays').val());
    
    $('#costDisplay').html('<div class="loading">Loading cost data</div>');
    
    $.ajax({
        url: '/api/costs',
        method: 'GET',
        data: { days: days },
        success: function(response) {
            if (response.success) {
                displayCosts(response.data);
            } else {
                showError('Failed to load costs: ' + (response.data.error || 'Unknown error'));
            }
        },
        error: function() {
            showError('Error loading costs');
        }
    });
}

function displayCosts(costData) {
    const container = $('#costDisplay');
    
    // Display total cost
    const html = `
        <div class="cost-summary">
            <div class="cost-card">
                <h4>Total Cost (${costData.period_days} days)</h4>
                <div class="amount">$${costData.total.toFixed(2)}</div>
            </div>
        </div>
    `;
    container.html(html);
    
    // Show chart
    $('#costChart').show();
    displayCostChart(costData.by_service);
}

function displayCostChart(serviceData) {
    const ctx = document.getElementById('costChart');
    
    if (costChart) {
        costChart.destroy();
    }
    
    // Calculate totals by service
    const labels = Object.keys(serviceData);
    const data = labels.map(service => {
        return serviceData[service].reduce((sum, item) => sum + item.cost, 0);
    });
    
    costChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Cost ($)',
                data: data,
                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                borderColor: '#667eea',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// ----------------------------------------------------------------------------
// BOTTLENECK DETECTION
// ----------------------------------------------------------------------------
function detectBottlenecks() {
    const region = getSelectedRegions()[0];
    
    $('#bottleneckDisplay').html('<div class="loading">Scanning for bottlenecks</div>');
    
    $.ajax({
        url: '/api/bottlenecks',
        method: 'GET',
        data: { region: region },
        success: function(response) {
            if (response.success) {
                displayBottlenecks(response.data);
            } else {
                showError('Failed to detect bottlenecks');
            }
        },
        error: function() {
            showError('Error detecting bottlenecks');
        }
    });
}

function displayBottlenecks(bottlenecks) {
    const container = $('#bottleneckDisplay');
    container.empty();
    
    let hasIssues = false;
    
    // High CPU resources
    if (bottlenecks.high_cpu.length > 0) {
        hasIssues = true;
        container.append('<h3 style="margin-top: 20px;">⚠️ High CPU Utilization</h3>');
        
        bottlenecks.high_cpu.forEach(item => {
            const html = `
                <div class="bottleneck-item ${item.severity}">
                    <h4>${item.resource_id} (${item.type})</h4>
                    <div class="bottleneck-metrics">
                        <div class="metric-box">
                            <label>Average CPU</label>
                            <div class="value">${item.avg_cpu}%</div>
                        </div>
                        <div class="metric-box">
                            <label>Peak CPU</label>
                            <div class="value">${item.max_cpu}%</div>
                        </div>
                        <div class="metric-box">
                            <label>Severity</label>
                            <div class="value">${item.severity.toUpperCase()}</div>
                        </div>
                    </div>
                </div>
            `;
            container.append(html);
        });
    }
    
    // Underutilized resources
    if (bottlenecks.underutilized.length > 0) {
        hasIssues = true;
        container.append('<h3 style="margin-top: 20px;">💡 Underutilized Resources</h3>');
        
        bottlenecks.underutilized.forEach(item => {
            const html = `
                <div class="bottleneck-item">
                    <h4>${item.resource_id} (${item.type})</h4>
                    <p>${item.recommendation}</p>
                    <div class="bottleneck-metrics">
                        <div class="metric-box">
                            <label>Average CPU</label>
                            <div class="value">${item.avg_cpu}%</div>
                        </div>
                    </div>
                </div>
            `;
            container.append(html);
        });
    }
    
    if (!hasIssues) {
        container.html('<div class="alert alert-success">✅ No issues detected! Resources are performing well.</div>');
    }
}

// ----------------------------------------------------------------------------
// UTILITY FUNCTIONS
// ----------------------------------------------------------------------------
function showError(message) {
    console.error(message);
    const html = '<div class="alert alert-error">' + message + '</div>';
    $('#resourceList').html(html);
}

// ----------------------------------------------------------------------------
// BACKGROUND MONITORING
// ----------------------------------------------------------------------------
function loadMonitoringStatus() {
    $.ajax({
        url: '/api/monitoring/status',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                updateMonitoringUI(response.data);
            }
        },
        error: function() {
            console.error('Error loading monitoring status');
        }
    });
}

function updateMonitoringUI(data) {
    const statusDot = $('.status-dot');
    const statusText = $('.status-text');
    
    if (data.enabled) {
        statusDot.removeClass('inactive').addClass('active');
        statusText.text('Monitoring Active (checks every ' + data.interval_minutes + ' minutes)');
        $('#startMonitoring').hide();
        $('#stopMonitoring').show();
    } else {
        statusDot.removeClass('active').addClass('inactive');
        statusText.text('Monitoring Inactive');
        $('#startMonitoring').show();
        $('#stopMonitoring').hide();
    }
    
    // Display monitored resources
    displayMonitoredResources(data.monitored_resources);
}

function displayMonitoredResources(resources) {
    const container = $('#monitoredResourcesList');
    
    if (!resources || resources.length === 0) {
        container.html('<p class="info-text" style="color: white;">No resources being monitored</p>');
        return;
    }
    
    let html = '<h4 style="margin-bottom: 10px; color: white;">Monitored Resources:</h4>';
    
    resources.forEach(resource => {
        html += `
            <div class="monitored-item">
                <div class="monitored-item-info">
                    <strong>${resource.id}</strong>
                    <small>${resource.type} • ${resource.region} • CPU threshold: ${resource.cpu_threshold || 80}%</small>
                </div>
                <button class="btn-remove" onclick="removeFromMonitoring('${resource.id}')">Remove</button>
            </div>
        `;
    });
    
    container.html(html);
}

function startMonitoring() {
    $.ajax({
        url: '/api/monitoring/start',
        method: 'POST',
        success: function(response) {
            if (response.success) {
                alert('Background monitoring started!');
                loadMonitoringStatus();
            }
        },
        error: function() {
            alert('Error starting monitoring');
        }
    });
}

function stopMonitoring() {
    if (!confirm('Stop background monitoring?')) {
        return;
    }
    
    $.ajax({
        url: '/api/monitoring/stop',
        method: 'POST',
        success: function(response) {
            if (response.success) {
                alert('Background monitoring stopped');
                loadMonitoringStatus();
            }
        },
        error: function() {
            alert('Error stopping monitoring');
        }
    });
}

function addSelectedToMonitoring() {
    if (selectedResources.length === 0) {
        alert('Please select resources first');
        return;
    }
    
    // Only support monitorable resource types
    const monitorable = ['ec2', 'rds', 'lambda'];
    const validResources = selectedResources.filter(r => monitorable.includes(r.type));
    
    if (validResources.length === 0) {
        alert('Selected resources cannot be monitored. Only EC2, RDS, and Lambda are supported.');
        return;
    }
    
    // Get custom threshold
    const threshold = prompt('Enter CPU threshold (%) for alerts:', '80');
    if (!threshold) return;
    
    let addedCount = 0;
    
    validResources.forEach(resource => {
        $.ajax({
            url: '/api/monitoring/add',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                id: resource.id,
                type: resource.type,
                region: resource.region,
                cpu_threshold: parseFloat(threshold)
            }),
            success: function(response) {
                addedCount++;
                if (addedCount === validResources.length) {
                    alert(`Added ${addedCount} resource(s) to monitoring`);
                    loadMonitoringStatus();
                }
            },
            error: function() {
                console.error('Error adding resource to monitoring');
            }
        });
    });
}

function removeFromMonitoring(resourceId) {
    if (!confirm('Remove from monitoring?')) {
        return;
    }
    
    $.ajax({
        url: '/api/monitoring/remove/' + resourceId,
        method: 'DELETE',
        success: function(response) {
            if (response.success) {
                loadMonitoringStatus();
            }
        },
        error: function() {
            alert('Error removing resource from monitoring');
        }
    });
}

function sendTestAlert() {
    if (!confirm('Send a test alert email?')) {
        return;
    }
    
    $.ajax({
        url: '/api/alerts/test',
        method: 'POST',
        success: function(response) {
            if (response.success) {
                alert('Test alert sent! Check your email.');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON ? xhr.responseJSON.error : 'Unknown error';
            alert('Error sending test alert: ' + error);
        }
    });
}
