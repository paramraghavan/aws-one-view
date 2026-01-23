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
    loadScheduledReports();
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
    
    // Cost report controls
    $('#generateReport').click(generateCostReport);
    $('#scheduleReport').click(scheduleCostReport);
    
    // Cost optimization
    $('#analyzeCosts').click(analyzeCostOptimization);
    
    // Security audit
    $('#runSecurityAudit').click(runSecurityAudit);
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
    table += '<th>Actions</th>';  // Add actions column
    table += '</tr></thead><tbody>';
    
    // Add rows
    resources.forEach(resource => {
        table += '<tr>';
        table += '<td><input type="checkbox" class="resource-checkbox" data-id="' + resource.id + '" data-region="' + resource.region + '"></td>';
        table += getRowContentForResource(currentResourceType, resource);
        // Add view details button
        table += '<td><button class="btn-details" data-id="' + resource.id + '" data-region="' + resource.region + '" data-type="' + currentResourceType + '">📋 Details</button></td>';
        table += '</tr>';
    });
    
    table += '</tbody></table>';
    container.html(table);
    
    // Setup checkbox handlers
    setupResourceCheckboxes();
    
    // Setup detail button handlers
    $('.btn-details').click(function() {
        const resourceId = $(this).data('id');
        const region = $(this).data('region');
        const type = $(this).data('type');
        showResourceDetails(resourceId, type, region);
    });
}

// ----------------------------------------------------------------------------
// RESOURCE DETAILS
// ----------------------------------------------------------------------------
function showResourceDetails(resourceId, resourceType, region) {
    // Show loading
    showDetailModal('Loading...', '<div class="loading">Fetching resource details</div>');
    
    $.ajax({
        url: '/api/resource/details',
        method: 'GET',
        data: {
            resource_id: resourceId,
            resource_type: resourceType,
            region: region
        },
        success: function(response) {
            if (response.success) {
                displayResourceDetails(response.data, resourceType);
            } else {
                showDetailModal('Error', '<div class="alert alert-error">' + response.error + '</div>');
            }
        },
        error: function() {
            showDetailModal('Error', '<div class="alert alert-error">Failed to load resource details</div>');
        }
    });
}

function displayResourceDetails(details, resourceType) {
    let html = '<div class="resource-details">';
    
    // Format details based on resource type
    if (resourceType === 'ec2') {
        html += `
            <div class="detail-section">
                <h4>📊 Current Status</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>State</label>
                        <span class="status-badge status-${details.state}">${details.state}</span>
                    </div>
                    <div class="detail-item">
                        <label>Current CPU</label>
                        <span class="metric-value">${details.current_cpu}%</span>
                    </div>
                    <div class="detail-item">
                        <label>Type</label>
                        <span>${details.type}</span>
                    </div>
                    <div class="detail-item">
                        <label>Availability Zone</label>
                        <span>${details.az}</span>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h4>🌐 Network</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>Private IP</label>
                        <span>${details.private_ip}</span>
                    </div>
                    <div class="detail-item">
                        <label>Public IP</label>
                        <span>${details.public_ip}</span>
                    </div>
                    <div class="detail-item">
                        <label>VPC</label>
                        <span>${details.vpc_id}</span>
                    </div>
                    <div class="detail-item">
                        <label>Subnet</label>
                        <span>${details.subnet_id}</span>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h4>🔒 Security</h4>
                <div class="detail-item">
                    <label>Security Groups</label>
                    <span>${details.security_groups.join(', ')}</span>
                </div>
            </div>
            
            <div class="detail-section">
                <h4>ℹ️ Info</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>Launch Time</label>
                        <span>${new Date(details.launch_time).toLocaleString()}</span>
                    </div>
                    <div class="detail-item">
                        <label>Platform</label>
                        <span>${details.platform}</span>
                    </div>
                    <div class="detail-item">
                        <label>Monitoring</label>
                        <span>${details.monitoring}</span>
                    </div>
                </div>
            </div>
        `;
        
        // Tags
        if (Object.keys(details.tags).length > 0) {
            html += '<div class="detail-section"><h4>🏷️ Tags</h4><div class="tags">';
            Object.entries(details.tags).forEach(([key, value]) => {
                html += `<span class="tag"><strong>${key}:</strong> ${value}</span>`;
            });
            html += '</div></div>';
        }
    } else if (resourceType === 'rds') {
        html += `
            <div class="detail-section">
                <h4>📊 Current Status</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>Status</label>
                        <span class="status-badge status-${details.status}">${details.status}</span>
                    </div>
                    <div class="detail-item">
                        <label>Current CPU</label>
                        <span class="metric-value">${details.current_cpu}%</span>
                    </div>
                    <div class="detail-item">
                        <label>Class</label>
                        <span>${details.class}</span>
                    </div>
                    <div class="detail-item">
                        <label>Multi-AZ</label>
                        <span>${details.multi_az ? 'Yes' : 'No'}</span>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h4>🗄️ Database</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>Engine</label>
                        <span>${details.engine} ${details.engine_version}</span>
                    </div>
                    <div class="detail-item">
                        <label>Endpoint</label>
                        <span>${details.endpoint}:${details.port}</span>
                    </div>
                    <div class="detail-item">
                        <label>Storage</label>
                        <span>${details.storage_gb} GB (${details.storage_type})</span>
                    </div>
                    <div class="detail-item">
                        <label>Backup Retention</label>
                        <span>${details.backup_retention} days</span>
                    </div>
                </div>
            </div>
        `;
    } else if (resourceType === 'lambda') {
        html += `
            <div class="detail-section">
                <h4>⚡ Function Configuration</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>Runtime</label>
                        <span>${details.runtime}</span>
                    </div>
                    <div class="detail-item">
                        <label>Memory</label>
                        <span>${details.memory_mb} MB</span>
                    </div>
                    <div class="detail-item">
                        <label>Timeout</label>
                        <span>${details.timeout_sec} seconds</span>
                    </div>
                    <div class="detail-item">
                        <label>Code Size</label>
                        <span>${(details.code_size_bytes / 1024 / 1024).toFixed(2)} MB</span>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h4>📈 Usage (Last 24h)</h4>
                <div class="detail-item">
                    <label>Invocations</label>
                    <span class="metric-value">${details.invocations_24h.toLocaleString()}</span>
                </div>
            </div>
            
            <div class="detail-section">
                <h4>ℹ️ Info</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>Handler</label>
                        <span>${details.handler}</span>
                    </div>
                    <div class="detail-item">
                        <label>Last Modified</label>
                        <span>${details.last_modified}</span>
                    </div>
                    <div class="detail-item">
                        <label>Layers</label>
                        <span>${details.layers}</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    html += '</div>';
    
    showDetailModal(details.id, html);
}

function showDetailModal(title, content) {
    // Create modal if it doesn't exist
    if ($('#detailModal').length === 0) {
        $('body').append(`
            <div id="detailModal" class="modal">
                <div class="modal-content">
                    <span class="modal-close">&times;</span>
                    <h2 id="modalTitle"></h2>
                    <div id="modalBody"></div>
                </div>
            </div>
        `);
        
        // Close button handler
        $('.modal-close').click(function() {
            $('#detailModal').hide();
        });
        
        // Click outside to close
        $('#detailModal').click(function(e) {
            if (e.target.id === 'detailModal') {
                $(this).hide();
            }
        });
    }
    
    // Set content and show
    $('#modalTitle').text(title);
    $('#modalBody').html(content);
    $('#detailModal').show();
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
    
    if (costData.error) {
        container.html(`<div class="alert alert-error">${costData.error}</div>`);
        return;
    }
    
    // Display total cost
    let html = `
        <div class="cost-summary">
            <div class="cost-card">
                <h4>Total Cost (${costData.period_days} days)</h4>
                <div class="amount">$${costData.total.toFixed(2)}</div>
            </div>
            <div class="cost-card">
                <h4>Services</h4>
                <div class="amount">${costData.service_count}</div>
            </div>
        </div>
    `;
    
    // Display breakdown by service
    if (costData.by_service && Object.keys(costData.by_service).length > 0) {
        html += '<h3 style="margin-top: 20px;">Cost Breakdown by Service</h3>';
        html += '<div class="service-costs">';
        
        // Sort and display all services
        Object.entries(costData.by_service).forEach(([service, data]) => {
            const color = data.total > 0 ? '#28a745' : '#999';
            html += `
                <div class="service-cost-item">
                    <div class="service-name">${service}</div>
                    <div class="service-cost" style="color: ${color};">
                        $${data.total.toFixed(2)} 
                        <span class="cost-percentage">(${data.percentage}%)</span>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
    }
    
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
    
    // Extract services and their totals
    const labels = [];
    const data = [];
    const colors = [];
    
    Object.entries(serviceData).forEach(([service, info]) => {
        if (info.total > 0) {  // Only show services with costs
            labels.push(service);
            data.push(info.total);
            // Color code by amount
            if (info.total > 1000) {
                colors.push('rgba(220, 53, 69, 0.6)');  // Red for expensive
            } else if (info.total > 100) {
                colors.push('rgba(255, 193, 7, 0.6)');  // Yellow for moderate
            } else {
                colors.push('rgba(40, 167, 69, 0.6)');  // Green for cheap
            }
        }
    });
    
    costChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Cost ($)',
                data: data,
                backgroundColor: colors,
                borderColor: colors.map(c => c.replace('0.6', '1')),
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const service = context.label;
                            const info = serviceData[service];
                            return [
                                `Total: $${context.parsed.y.toFixed(2)}`,
                                `Percentage: ${info.percentage}%`
                            ];
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(2);
                        }
                    }
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

// ----------------------------------------------------------------------------
// COST REPORTS
// ----------------------------------------------------------------------------
function generateCostReport() {
    if (selectedResources.length === 0) {
        alert('Please select resources first');
        return;
    }
    
    const period = $('#reportPeriod').val();
    const sendEmail = $('#emailReport').is(':checked');
    
    // Prepare resources with names
    const resources = selectedResources.map(r => ({
        id: r.id,
        type: r.type,
        region: r.region,
        name: r.id  // Could get name from tags if available
    }));
    
    // Show loading
    $('#reportResult').html('<div class="loading">Generating cost report...</div>').show();
    
    $.ajax({
        url: '/api/reports/generate',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            resources: resources,
            period: period,
            send_email: sendEmail
        }),
        success: function(response) {
            if (response.success) {
                displayReportResult(response.data, sendEmail);
            } else {
                $('#reportResult').html(`<div class="alert alert-error">${response.error}</div>`);
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON ? xhr.responseJSON.error : 'Unknown error';
            $('#reportResult').html(`<div class="alert alert-error">Error: ${error}</div>`);
        }
    });
}

function displayReportResult(report, emailSent) {
    let html = `
        <div class="report-result">
            <h4>${report.title}</h4>
            <div class="report-summary">
                <div class="report-stat">
                    <label>Total Cost</label>
                    <span class="cost-value">$${report.total_cost.toFixed(2)}</span>
                </div>
                <div class="report-stat">
                    <label>Resources</label>
                    <span>${report.resource_count}</span>
                </div>
                <div class="report-stat">
                    <label>Period</label>
                    <span>${report.start_date} to ${report.end_date}</span>
                </div>
            </div>
    `;
    
    if (emailSent) {
        html += '<div class="alert alert-success">✅ Report sent via email!</div>';
    }
    
    html += '<h5>Cost Breakdown:</h5><div class="report-breakdown">';
    
    report.resources.forEach(resource => {
        const statusText = resource.estimated ? ' (estimated)' : '';
        const errorText = resource.error ? ` - Error: ${resource.error}` : '';
        html += `
            <div class="report-item">
                <div class="report-item-name">${resource.name}</div>
                <div class="report-item-cost">$${resource.cost.toFixed(2)}${statusText}${errorText}</div>
            </div>
        `;
    });
    
    html += '</div></div>';
    
    $('#reportResult').html(html).show();
}

function scheduleCostReport() {
    if (selectedResources.length === 0) {
        alert('Please select resources first');
        return;
    }
    
    const name = $('#reportName').val().trim();
    if (!name) {
        alert('Please enter a report name');
        return;
    }
    
    const period = $('#scheduledPeriod').val();
    const schedule = $('#reportSchedule').val();
    
    // Prepare resources
    const resources = selectedResources.map(r => ({
        id: r.id,
        type: r.type,
        region: r.region,
        name: r.id
    }));
    
    $.ajax({
        url: '/api/reports/schedule',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            name: name,
            resources: resources,
            period: period,
            schedule: schedule
        }),
        success: function(response) {
            if (response.success) {
                alert('Report scheduled successfully!');
                $('#reportName').val('');
                loadScheduledReports();
            } else {
                alert('Error: ' + response.error);
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON ? xhr.responseJSON.error : 'Unknown error';
            alert('Error scheduling report: ' + error);
        }
    });
}

function loadScheduledReports() {
    $.ajax({
        url: '/api/reports/scheduled',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                displayScheduledReports(response.data);
            }
        },
        error: function() {
            console.error('Error loading scheduled reports');
        }
    });
}

function displayScheduledReports(reports) {
    const container = $('#scheduledReportsContent');
    
    if (!reports || reports.length === 0) {
        container.html('<p class="info-text">No scheduled reports</p>');
        return;
    }
    
    let html = '';
    
    reports.forEach(report => {
        html += `
            <div class="scheduled-report-item">
                <div class="report-info">
                    <strong>${report.name}</strong>
                    <div class="report-details">
                        ${report.period} report • ${report.schedule} • ${report.resources.length} resources
                    </div>
                </div>
                <button class="btn-remove" onclick="removeScheduledReport('${report.name}')">Remove</button>
            </div>
        `;
    });
    
    container.html(html);
}

function removeScheduledReport(name) {
    if (!confirm(`Remove scheduled report "${name}"?`)) {
        return;
    }
    
    $.ajax({
        url: '/api/reports/scheduled/' + encodeURIComponent(name),
        method: 'DELETE',
        success: function(response) {
            if (response.success) {
                loadScheduledReports();
            } else {
                alert('Error: ' + response.error);
            }
        },
        error: function() {
            alert('Error removing scheduled report');
        }
    });
}

// ----------------------------------------------------------------------------
// COST OPTIMIZATION
// ----------------------------------------------------------------------------
function analyzeCostOptimization() {
    const regions = $('#regionSelect').val() || [];
    
    if (regions.length === 0) {
        alert('Please select at least one region first');
        return;
    }
    
    $('#optimizationDisplay').html('<div class="loading">Analyzing cost savings opportunities...</div>');
    
    $.ajax({
        url: '/api/optimization/analyze',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ regions: regions }),
        success: function(response) {
            if (response.success) {
                displayOptimizationResults(response.data);
            } else {
                $('#optimizationDisplay').html(`<div class="alert alert-error">${response.error}</div>`);
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON ? xhr.responseJSON.error : 'Unknown error';
            $('#optimizationDisplay').html(`<div class="alert alert-error">Error: ${error}</div>`);
        }
    });
}

function displayOptimizationResults(data) {
    let html = `
        <div class="optimization-results">
            <div class="optimization-summary">
                <div class="savings-card">
                    <h3>💰 Potential Monthly Savings</h3>
                    <div class="savings-amount">$${data.total_monthly_savings.toFixed(2)}</div>
                    <div class="savings-annual">$${(data.total_monthly_savings * 12).toFixed(2)}/year</div>
                </div>
            </div>
    `;
    
    // Quick Wins
    if (data.quick_wins && data.quick_wins.length > 0) {
        html += '<div class="quick-wins"><h3>⚡ Quick Wins (Easy to Implement)</h3>';
        data.quick_wins.forEach(item => {
            html += `
                <div class="optimization-item ${item.severity}">
                    <div class="opt-header">
                        <span class="opt-resource">${item.resource_id}</span>
                        <span class="opt-savings">Save $${item.monthly_savings.toFixed(2)}/month</span>
                    </div>
                    <div class="opt-recommendation">${item.recommendation}</div>
                </div>
            `;
        });
        html += '</div>';
    }
    
    // Idle Instances
    if (data.idle_instances && data.idle_instances.length > 0) {
        html += `<div class="optimization-category"><h4>🛑 Idle Instances (${data.idle_instances.length})</h4>`;
        data.idle_instances.slice(0, 5).forEach(item => {
            html += `
                <div class="optimization-item">
                    <strong>${item.resource_id}</strong> - ${item.instance_type} - Avg CPU: ${item.avg_cpu_7d}%
                    <div class="opt-savings">Save $${item.monthly_savings.toFixed(2)}/month</div>
                </div>
            `;
        });
        if (data.idle_instances.length > 5) {
            html += `<div class="more-items">...and ${data.idle_instances.length - 5} more</div>`;
        }
        html += '</div>';
    }
    
    // Right-Sizing
    if (data.underutilized_instances && data.underutilized_instances.length > 0) {
        html += `<div class="optimization-category"><h4>📉 Right-Sizing Opportunities (${data.underutilized_instances.length})</h4>`;
        data.underutilized_instances.slice(0, 5).forEach(item => {
            html += `
                <div class="optimization-item">
                    <strong>${item.resource_id}</strong>: ${item.current_type} → ${item.suggested_type}
                    <div class="opt-savings">Save $${item.monthly_savings.toFixed(2)}/month</div>
                </div>
            `;
        });
        html += '</div>';
    }
    
    // Unattached Volumes
    if (data.unattached_volumes && data.unattached_volumes.length > 0) {
        html += `<div class="optimization-category"><h4>💾 Unattached Volumes (${data.unattached_volumes.length})</h4>`;
        data.unattached_volumes.slice(0, 5).forEach(item => {
            html += `
                <div class="optimization-item">
                    <strong>${item.resource_id}</strong> - ${item.size_gb}GB - ${item.age_days} days old
                    <div class="opt-savings">Save $${item.monthly_savings.toFixed(2)}/month</div>
                </div>
            `;
        });
        html += '</div>';
    }
    
    // Reserved Instances
    if (data.reserved_instance_opportunities && data.reserved_instance_opportunities.length > 0) {
        html += `<div class="optimization-category"><h4>📅 Reserved Instance Opportunities (${data.reserved_instance_opportunities.length})</h4>`;
        data.reserved_instance_opportunities.slice(0, 3).forEach(item => {
            html += `
                <div class="optimization-item">
                    <strong>${item.resource_id}</strong> - ${item.instance_type} - Running ${item.running_days} days
                    <div class="opt-savings">Save $${item.monthly_savings.toFixed(2)}/month ($${item.annual_savings.toFixed(2)}/year)</div>
                </div>
            `;
        });
        html += '</div>';
    }
    
    html += '</div>';
    $('#optimizationDisplay').html(html);
}

// ----------------------------------------------------------------------------
// SECURITY AUDIT
// ----------------------------------------------------------------------------
function runSecurityAudit() {
    const regions = $('#regionSelect').val() || [];
    
    if (regions.length === 0) {
        alert('Please select at least one region first');
        return;
    }
    
    $('#securityDisplay').html('<div class="loading">Running security audit...</div>');
    
    $.ajax({
        url: '/api/security/audit',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ regions: regions }),
        success: function(response) {
            if (response.success) {
                displaySecurityResults(response.data);
            } else {
                $('#securityDisplay').html(`<div class="alert alert-error">${response.error}</div>`);
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON ? xhr.responseJSON.error : 'Unknown error';
            $('#securityDisplay').html(`<div class="alert alert-error">Error: ${error}</div>`);
        }
    });
}

function displaySecurityResults(data) {
    const score = data.security_score;
    const scoreClass = score >= 80 ? 'good' : score >= 60 ? 'medium' : 'poor';
    
    let html = `
        <div class="security-results">
            <div class="security-score-card ${scoreClass}">
                <h3>🔒 Security Score</h3>
                <div class="score-display">${score}/100</div>
                <div class="score-details">${data.passed_checks} of ${data.total_checks} checks passed</div>
            </div>
    `;
    
    // Critical Issues
    if (data.critical && data.critical.length > 0) {
        html += `<div class="security-category critical"><h4>🔴 Critical Issues (${data.critical.length})</h4>`;
        data.critical.forEach(finding => {
            html += `
                <div class="security-finding">
                    <div class="finding-header">
                        <strong>${finding.resource_id || finding.resource_type}</strong>
                        <span class="finding-severity critical">CRITICAL</span>
                    </div>
                    <div class="finding-issue">${finding.issue}</div>
                    <div class="finding-recommendation">💡 ${finding.recommendation}</div>
                </div>
            `;
        });
        html += '</div>';
    }
    
    // High Priority
    if (data.high && data.high.length > 0) {
        html += `<div class="security-category high"><h4>⚠️ High Priority (${data.high.length})</h4>`;
        data.high.slice(0, 5).forEach(finding => {
            html += `
                <div class="security-finding">
                    <div class="finding-header">
                        <strong>${finding.resource_id || finding.resource_type}</strong>
                        <span class="finding-severity high">HIGH</span>
                    </div>
                    <div class="finding-issue">${finding.issue}</div>
                    <div class="finding-recommendation">💡 ${finding.recommendation}</div>
                </div>
            `;
        });
        if (data.high.length > 5) {
            html += `<div class="more-items">...and ${data.high.length - 5} more high priority issues</div>`;
        }
        html += '</div>';
    }
    
    // Medium Priority
    if (data.medium && data.medium.length > 0) {
        html += `<div class="security-category medium"><h4>⚡ Medium Priority (${data.medium.length})</h4>`;
        data.medium.slice(0, 3).forEach(finding => {
            html += `
                <div class="security-finding">
                    <div class="finding-header">
                        <strong>${finding.resource_id || finding.resource_type}</strong>
                        <span class="finding-severity medium">MEDIUM</span>
                    </div>
                    <div class="finding-issue">${finding.issue}</div>
                </div>
            `;
        });
        if (data.medium.length > 3) {
            html += `<div class="more-items">...and ${data.medium.length - 3} more medium priority issues</div>`;
        }
        html += '</div>';
    }
    
    // Success summary
    if (score >= 80) {
        html += '<div class="alert alert-success">✅ Good security posture! Address the remaining issues to improve further.</div>';
    } else if (score >= 60) {
        html += '<div class="alert alert-warning">⚠️ Moderate security. Focus on critical and high priority issues first.</div>';
    } else {
        html += '<div class="alert alert-error">🔴 Security needs immediate attention. Address critical issues now!</div>';
    }
    
    html += '</div>';
    $('#securityDisplay').html(html);
}
