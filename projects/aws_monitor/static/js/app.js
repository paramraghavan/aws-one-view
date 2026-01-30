// AWS Monitor - UI Controller

let discoveredResources = null;
let selectedResources = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
});

function setupEventListeners() {
    // Discover resources
    document.getElementById('discover-btn').addEventListener('click', discoverResources);
    
    // Get metrics
    document.getElementById('metrics-btn').addEventListener('click', getMetrics);
    
    // Analyze costs
    document.getElementById('cost-btn').addEventListener('click', analyzeCosts);
    
    // Check alerts
    document.getElementById('alerts-btn').addEventListener('click', checkAlerts);
    
    // Generate script
    document.getElementById('generate-script-btn').addEventListener('click', generateScript);
    
    // Load all regions
    document.getElementById('load-more-regions').addEventListener('click', loadAllRegions);
    
    // Resource type selection buttons
    document.getElementById('select-all-types').addEventListener('click', () => {
        document.querySelectorAll('.resource-type-filter').forEach(cb => cb.checked = true);
    });
    
    document.getElementById('deselect-all-types').addEventListener('click', () => {
        document.querySelectorAll('.resource-type-filter').forEach(cb => cb.checked = false);
    });
    
    document.getElementById('select-common-types').addEventListener('click', () => {
        const commonTypes = ['ec2', 'rds', 's3'];
        document.querySelectorAll('.resource-type-filter').forEach(cb => {
            cb.checked = commonTypes.includes(cb.value);
        });
    });
}

async function discoverResources() {
    const btn = document.getElementById('discover-btn');
    const status = document.getElementById('discover-status');
    
    // Get selected regions
    const regions = Array.from(document.querySelectorAll('#region-selection input[type="checkbox"]:checked'))
        .map(cb => cb.value);
    
    if (regions.length === 0) {
        showStatus(status, 'Please select at least one region', 'error');
        return;
    }
    
    // Get selected resource types
    const resourceTypes = Array.from(document.querySelectorAll('.resource-type-filter:checked'))
        .map(cb => cb.value);
    
    if (resourceTypes.length === 0) {
        showStatus(status, 'Please select at least one resource type to discover', 'error');
        return;
    }
    
    // Get filters
    const filters = {};
    const tagKey = document.getElementById('filter-tag-key').value.trim();
    const tagValue = document.getElementById('filter-tag-value').value.trim();
    if (tagKey && tagValue) {
        filters.tags = {[tagKey]: tagValue};
    }
    
    const names = document.getElementById('filter-names').value.trim();
    if (names) {
        filters.names = names.split(',').map(s => s.trim());
    }
    
    const ids = document.getElementById('filter-ids').value.trim();
    if (ids) {
        filters.ids = ids.split(',').map(s => s.trim());
    }
    
    // Show loading
    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span> Discovering...';
    showStatus(status, `Scanning ${resourceTypes.join(', ')} in ${regions.join(', ')}...`, 'loading');
    
    try {
        const response = await fetch('/api/discover', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({regions, filters, resource_types: resourceTypes})
        });
        
        if (!response.ok) throw new Error('Discovery failed');
        
        discoveredResources = await response.json();
        
        // Display results
        displayResourceSummary(discoveredResources.summary);
        displayResourceList(discoveredResources.regions);
        
        const totalResources = Object.values(discoveredResources.summary).reduce((a, b) => a + b, 0);
        showStatus(status, `Found ${totalResources} resources (${resourceTypes.join(', ')})`, 'success');
        
        // Enable metric and alert buttons
        document.getElementById('metrics-btn').disabled = false;
        document.getElementById('alerts-btn').disabled = false;
        
    } catch (error) {
        showStatus(status, `Error: ${error.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🔍 Discover Resources';
    }
}

function displayResourceSummary(summary) {
    const container = document.getElementById('resource-summary');
    container.innerHTML = '<h3>Resource Summary</h3>';
    
    const grid = document.createElement('div');
    grid.style.display = 'grid';
    grid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(150px, 1fr))';
    grid.style.gap = '15px';
    grid.style.marginTop = '15px';
    
    for (const [type, count] of Object.entries(summary)) {
        if (count > 0) {
            const card = document.createElement('div');
            card.className = 'summary-card';
            card.innerHTML = `
                <div class="number">${count}</div>
                <div class="label">${type.toUpperCase()}</div>
            `;
            grid.appendChild(card);
        }
    }
    
    container.appendChild(grid);
}

function displayResourceList(regionsData) {
    const container = document.getElementById('resource-list');
    container.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <h3>Resources by Type</h3>
            <button id="export-csv-btn" class="secondary-btn">📥 Export to CSV</button>
        </div>
    `;
    
    // Group resources by type across all regions
    const resourcesByType = {};
    
    for (const [region, resourceTypes] of Object.entries(regionsData)) {
        for (const [type, resources] of Object.entries(resourceTypes)) {
            if (resources.length === 0) continue;
            
            if (!resourcesByType[type]) {
                resourcesByType[type] = [];
            }
            
            // Add region info to each resource
            resources.forEach(resource => {
                resourcesByType[type].push({...resource, _region: region});
            });
        }
    }
    
    // Create collapsible section for each resource type
    for (const [type, resources] of Object.entries(resourcesByType)) {
        if (resources.length === 0) continue;
        
        const section = document.createElement('div');
        section.className = 'resource-section';
        section.style.marginTop = '20px';
        section.style.border = '1px solid #dee2e6';
        section.style.borderRadius = '4px';
        
        // Collapsible header
        const header = document.createElement('div');
        header.className = 'resource-section-header';
        header.style.padding = '15px';
        header.style.backgroundColor = '#f8f9fa';
        header.style.cursor = 'pointer';
        header.style.display = 'flex';
        header.style.justifyContent = 'space-between';
        header.style.alignItems = 'center';
        header.style.borderBottom = '1px solid #dee2e6';
        
        // Calculate health score
        const healthScore = calculateHealthScore(type, resources);
        const healthColor = healthScore >= 80 ? '#28a745' : healthScore >= 60 ? '#ffc107' : '#dc3545';
        
        const headerText = document.createElement('div');
        headerText.innerHTML = `
            <strong>${type.toUpperCase()}</strong>
            <span style="margin-left: 10px; color: #666;">${resources.length} resources</span>
            <span style="margin-left: 10px; padding: 3px 8px; background: ${healthColor}; color: white; border-radius: 3px; font-size: 0.85em;">
                Health: ${healthScore}%
            </span>
        `;
        
        const toggleIcon = document.createElement('span');
        toggleIcon.className = 'toggle-icon';
        toggleIcon.textContent = '▼';
        toggleIcon.style.transition = 'transform 0.3s';
        
        header.appendChild(headerText);
        header.appendChild(toggleIcon);
        
        // Content area (initially hidden)
        const content = document.createElement('div');
        content.className = 'resource-section-content';
        content.style.display = 'none';
        content.style.padding = '15px';
        
        // Create table with enhanced columns
        const table = document.createElement('table');
        table.className = 'resource-table';
        
        // Table header with enhanced columns
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        headerRow.innerHTML = `
            <th><input type="checkbox" class="select-all" data-type="${type}"></th>
            <th>Status</th>
            <th>Name/ID</th>
            <th>Type/Class</th>
            <th>Region</th>
            <th>Tags</th>
            <th>Quick Actions</th>
            <th>Links</th>
        `;
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Table body with enhanced cells
        const tbody = document.createElement('tbody');
        resources.forEach(resource => {
            const row = document.createElement('tr');
            const resourceId = resource.id || resource.name;
            const region = resource._region;
            
            // Status indicator
            const status = resource.state || resource.status || 'unknown';
            const statusColor = getStatusColor(status);
            
            // Tags display
            const tags = resource.tags || {};
            const tagCount = Object.keys(tags).length;
            const tagDisplay = tagCount > 0 ? `${tagCount} tags` : 'No tags';
            
            row.innerHTML = `
                <td><input type="checkbox" class="resource-checkbox" data-type="${type}" data-id="${resourceId}" data-region="${region}"></td>
                <td><span class="status-indicator" style="background: ${statusColor};" title="${status}"></span></td>
                <td>
                    <strong>${resource.name || resource.id || 'N/A'}</strong>
                    ${getResourceAge(resource)}
                </td>
                <td>${resource.type || resource.class || resource.engine || resource.runtime || 'N/A'}</td>
                <td><span class="region-badge">${region}</span></td>
                <td>
                    <span class="tag-count" title="${JSON.stringify(tags, null, 2).replace(/"/g, '&quot;')}">${tagDisplay}</span>
                </td>
                <td>${getQuickActions(type, resource, region)}</td>
                <td>
                    <button class="link-btn" onclick="openInAWSConsole('${type}', '${resourceId}', '${region}')" title="Open in AWS Console">🔗 Console</button>
                    <button class="details-btn" data-type="${type}" data-id="${resourceId}" data-region="${region}">Details</button>
                </td>
            `;
            tbody.appendChild(row);
        });
        table.appendChild(tbody);
        
        content.appendChild(table);
        
        // Toggle functionality
        header.addEventListener('click', () => {
            if (content.style.display === 'none') {
                content.style.display = 'block';
                toggleIcon.style.transform = 'rotate(180deg)';
            } else {
                content.style.display = 'none';
                toggleIcon.style.transform = 'rotate(0deg)';
            }
        });
        
        section.appendChild(header);
        section.appendChild(content);
        container.appendChild(section);
    }
    
    // Add select-all handlers
    document.querySelectorAll('.select-all').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const type = e.target.dataset.type;
            const checkboxes = document.querySelectorAll(`.resource-checkbox[data-type="${type}"]`);
            checkboxes.forEach(cb => cb.checked = e.target.checked);
            updateSelectedResources();
        });
    });
    
    // Track selected resources
    document.querySelectorAll('.resource-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedResources);
    });
    
    // Add details button handlers
    document.querySelectorAll('.details-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const type = e.target.dataset.type;
            const id = e.target.dataset.id;
            const region = e.target.dataset.region;
            showResourceDetails(type, id, region);
        });
    });
    
    // Add export CSV handler
    document.getElementById('export-csv-btn').addEventListener('click', () => {
        exportToCSV(resourcesByType);
    });
}

function getResourceDetails(type, resource) {
    if (type === 'ec2') {
        return `${resource.private_ip || 'N/A'} | AZ: ${resource.az || 'N/A'}`;
    } else if (type === 'rds') {
        return `${resource.engine} ${resource.version || ''} | Multi-AZ: ${resource.multi_az ? 'Yes' : 'No'}`;
    } else if (type === 'lambda') {
        return `${resource.memory || 0} MB | Timeout: ${resource.timeout || 0}s`;
    } else if (type === 'eks') {
        return `Version ${resource.version || 'N/A'} | Nodes: ${resource.node_groups?.length || 0}`;
    } else if (type === 'emr') {
        return `${resource.release_label || 'N/A'}`;
    } else if (type === 'ebs') {
        return `${resource.size} GB | ${resource.type} | Encrypted: ${resource.encrypted ? 'Yes' : 'No'}`;
    }
    return 'N/A';
}

function getStatusColor(status) {
    const statusLower = (status || 'unknown').toLowerCase();
    
    // Green statuses (healthy/running)
    if (statusLower === 'running' || 
        statusLower === 'available' || 
        statusLower === 'active' ||
        statusLower === 'waiting' ||      // EMR waiting for work
        statusLower === 'bootstrapping' || // EMR starting up
        statusLower === 'starting') {      // EMR/EC2 starting
        return '#28a745';  // Green
    }
    
    // Yellow statuses (transitioning/stopped)
    else if (statusLower === 'stopped' || 
             statusLower === 'stopping' ||
             statusLower === 'terminating' ||
             statusLower === 'pending') {
        return '#ffc107';  // Yellow
    }
    
    // Red statuses (failed/terminated)
    else if (statusLower === 'terminated' || 
             statusLower === 'failed' || 
             statusLower === 'error' ||
             statusLower === 'terminated_with_errors') {
        return '#dc3545';  // Red
    }
    
    // Gray for unknown/undefined
    else {
        return '#6c757d';  // Gray
    }
}

function calculateHealthScore(type, resources) {
    // Simple health score based on resource state
    let healthy = 0;
    
    resources.forEach(r => {
        const status = (r.state || r.status || '').toLowerCase();
        
        // Lambda functions don't have status - they're always healthy if they exist
        if (type === 'lambda' || type === 's3') {
            healthy++;
        }
        // For other resources, check status
        else if (status === 'running' || 
                 status === 'available' || 
                 status === 'active' ||
                 status === 'waiting' ||      // EMR waiting is healthy
                 status === 'bootstrapping' || // EMR bootstrapping is healthy
                 status === 'starting') {      // Starting is transitioning to healthy
            healthy++;
        }
    });
    
    return Math.round((healthy / resources.length) * 100);
}

function getResourceAge(resource) {
    // If resource has created timestamp, show age
    if (resource.created) {
        try {
            const created = new Date(resource.created);
            const now = new Date();
            const days = Math.floor((now - created) / (1000 * 60 * 60 * 24));
            if (days > 0) {
                return `<br><small style="color: #666;">${days} days old</small>`;
            }
        } catch (e) {
            // Ignore parsing errors
        }
    }
    return '';
}

function getQuickActions(type, resource, region) {
    let actions = '';
    
    if (type === 'ec2') {
        if (resource.public_ip) {
            actions += `<button class="copy-btn" onclick="copyToClipboard('${resource.public_ip}')" title="Copy Public IP">📋 ${resource.public_ip}</button>`;
        }
        if (resource.private_ip) {
            actions += ` <button class="copy-btn" onclick="copyToClipboard('${resource.private_ip}')" title="Copy Private IP">📋 ${resource.private_ip}</button>`;
        }
    } else if (type === 'rds') {
        if (resource.endpoint) {
            actions += `<button class="copy-btn" onclick="copyToClipboard('${resource.endpoint}')" title="Copy Endpoint">📋 Endpoint</button>`;
        }
    } else if (type === 's3') {
        actions += `<button class="copy-btn" onclick="copyToClipboard('s3://${resource.name}')" title="Copy S3 URI">📋 s3://${resource.name}</button>`;
    } else if (type === 'eks') {
        if (resource.endpoint) {
            actions += `<button class="copy-btn" onclick="copyToClipboard('${resource.endpoint}')" title="Copy Endpoint">📋 Endpoint</button>`;
        }
    }
    
    return actions || '<small style="color: #999;">-</small>';
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        // Show toast notification
        const toast = document.createElement('div');
        toast.textContent = '✅ Copied!';
        toast.style.position = 'fixed';
        toast.style.bottom = '20px';
        toast.style.right = '20px';
        toast.style.background = '#28a745';
        toast.style.color = 'white';
        toast.style.padding = '10px 20px';
        toast.style.borderRadius = '4px';
        toast.style.zIndex = '10000';
        toast.style.animation = 'fadeIn 0.3s, fadeOut 0.3s 2s';
        
        document.body.appendChild(toast);
        setTimeout(() => document.body.removeChild(toast), 2500);
    }).catch(err => {
        alert('Failed to copy: ' + err);
    });
}

function openInAWSConsole(type, resourceId, region) {
    let url = '';
    
    if (type === 'ec2') {
        url = `https://console.aws.amazon.com/ec2/v2/home?region=${region}#Instances:instanceId=${resourceId}`;
    } else if (type === 'rds') {
        url = `https://console.aws.amazon.com/rds/home?region=${region}#database:id=${resourceId}`;
    } else if (type === 's3') {
        url = `https://s3.console.aws.amazon.com/s3/buckets/${resourceId}`;
    } else if (type === 'lambda') {
        url = `https://console.aws.amazon.com/lambda/home?region=${region}#/functions/${resourceId}`;
    } else if (type === 'eks') {
        url = `https://console.aws.amazon.com/eks/home?region=${region}#/clusters/${resourceId}`;
    } else if (type === 'emr') {
        url = `https://console.aws.amazon.com/emr/home?region=${region}#cluster-details/${resourceId}`;
    }
    
    if (url) {
        window.open(url, '_blank');
    } else {
        alert('AWS Console link not available for this resource type');
    }
}

function exportToCSV(resourcesByType) {
    let csv = 'Resource Type,Name/ID,Status,Type/Class,Region,Tags\n';
    
    for (const [type, resources] of Object.entries(resourcesByType)) {
        resources.forEach(resource => {
            const name = resource.name || resource.id || 'N/A';
            const status = resource.state || resource.status || 'N/A';
            const resourceType = resource.type || resource.class || resource.engine || resource.runtime || 'N/A';
            const region = resource._region || 'N/A';
            const tags = JSON.stringify(resource.tags || {});
            
            csv += `${type},${name},${status},${resourceType},${region},"${tags}"\n`;
        });
    }
    
    // Download CSV
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `aws-resources-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
}

function updateSelectedResources() {
    selectedResources = Array.from(document.querySelectorAll('.resource-checkbox:checked'))
        .map(cb => ({
            type: cb.dataset.type,
            id: cb.dataset.id,
            region: cb.dataset.region
        }));
}

function showResourceDetails(type, id, region) {
    // Find the resource in discoveredResources
    let resource = null;
    if (discoveredResources && discoveredResources.regions && discoveredResources.regions[region]) {
        const resourceList = discoveredResources.regions[region][type];
        if (resourceList) {
            resource = resourceList.find(r => (r.id || r.name) === id);
        }
    }
    
    if (!resource) {
        alert('Resource not found');
        return;
    }
    
    // Create modal
    const modal = document.createElement('div');
    modal.style.position = 'fixed';
    modal.style.top = '0';
    modal.style.left = '0';
    modal.style.width = '100%';
    modal.style.height = '100%';
    modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
    modal.style.display = 'flex';
    modal.style.alignItems = 'center';
    modal.style.justifyContent = 'center';
    modal.style.zIndex = '1000';
    
    const modalContent = document.createElement('div');
    modalContent.style.backgroundColor = 'white';
    modalContent.style.padding = '30px';
    modalContent.style.borderRadius = '8px';
    modalContent.style.maxWidth = '800px';
    modalContent.style.maxHeight = '80vh';
    modalContent.style.overflow = 'auto';
    modalContent.style.boxShadow = '0 4px 20px rgba(0,0,0,0.3)';
    
    // Build details HTML
    let detailsHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h2 style="margin: 0; color: #667eea;">${type.toUpperCase()} Details</h2>
            <button id="close-modal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
        </div>
        <div style="border-top: 2px solid #667eea; padding-top: 20px;">
    `;
    
    // Display all resource properties
    for (const [key, value] of Object.entries(resource)) {
        if (key.startsWith('_')) continue; // Skip internal properties
        
        let displayValue = value;
        if (typeof value === 'object' && value !== null) {
            displayValue = '<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow: auto;">' + 
                          JSON.stringify(value, null, 2) + '</pre>';
        } else if (typeof value === 'boolean') {
            displayValue = value ? 'Yes' : 'No';
        } else if (value === null || value === undefined) {
            displayValue = 'N/A';
        }
        
        detailsHTML += `
            <div style="margin-bottom: 15px; display: grid; grid-template-columns: 200px 1fr; gap: 10px;">
                <strong style="color: #555;">${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong>
                <span>${displayValue}</span>
            </div>
        `;
    }
    
    detailsHTML += '</div>';
    modalContent.innerHTML = detailsHTML;
    
    modal.appendChild(modalContent);
    document.body.appendChild(modal);
    
    // Close handlers
    document.getElementById('close-modal').addEventListener('click', () => {
        document.body.removeChild(modal);
    });
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    });
}

async function getMetrics() {
    if (selectedResources.length === 0) {
        alert('Please select resources first');
        return;
    }
    
    const btn = document.getElementById('metrics-btn');
    const results = document.getElementById('metrics-results');
    const period = parseInt(document.getElementById('metrics-period').value);
    
    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span> Loading...';
    results.innerHTML = '<p class="status loading">Collecting metrics...</p>';
    
    try {
        const response = await fetch('/api/metrics', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({resources: selectedResources, period})
        });
        
        if (!response.ok) throw new Error('Failed to get metrics');
        
        const metrics = await response.json();
        displayMetrics(metrics);
        
    } catch (error) {
        results.innerHTML = `<p class="status error">Error: ${error.message}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = '📊 Get Metrics';
    }
}

function displayMetrics(metrics) {
    const container = document.getElementById('metrics-results');
    container.innerHTML = '<h3>Performance Metrics</h3>';
    
    for (const [resourceKey, resourceMetrics] of Object.entries(metrics)) {
        if (resourceMetrics.error) {
            container.innerHTML += `<p class="status error">${resourceKey}: ${resourceMetrics.error}</p>`;
            continue;
        }
        
        const card = document.createElement('div');
        card.className = 'metric-card';
        card.innerHTML = `<h4>${resourceKey}</h4>`;
        
        const grid = document.createElement('div');
        grid.className = 'metric-grid';
        
        for (const [metricName, metricData] of Object.entries(resourceMetrics)) {
            if (typeof metricData === 'object' && metricData !== null) {
                const item = document.createElement('div');
                item.className = 'metric-item';
                
                let value = metricData.current || metricData.total || metricData.avg || 0;
                value = typeof value === 'number' ? value.toFixed(2) : value;
                
                item.innerHTML = `
                    <div class="label">${formatMetricName(metricName)}</div>
                    <div class="value">${value}</div>
                    <div style="font-size: 0.85em; color: #667eea; margin-top: 8px; font-weight: 500;">
                        <span style="opacity: 0.8;">👆</span> Click for details
                    </div>
                `;
                
                // Add click handler to show details
                item.addEventListener('click', () => {
                    showMetricDetails(resourceKey, metricName, metricData);
                });
                
                grid.appendChild(item);
            }
        }
        
        card.appendChild(grid);
        container.appendChild(card);
    }
}

function showMetricDetails(resourceKey, metricName, metricData) {
    // Create modal
    const modal = document.createElement('div');
    modal.style.position = 'fixed';
    modal.style.top = '0';
    modal.style.left = '0';
    modal.style.width = '100%';
    modal.style.height = '100%';
    modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
    modal.style.display = 'flex';
    modal.style.alignItems = 'center';
    modal.style.justifyContent = 'center';
    modal.style.zIndex = '1000';
    
    const modalContent = document.createElement('div');
    modalContent.style.backgroundColor = 'white';
    modalContent.style.padding = '30px';
    modalContent.style.borderRadius = '8px';
    modalContent.style.maxWidth = '600px';
    modalContent.style.boxShadow = '0 4px 20px rgba(0,0,0,0.3)';
    
    // Build metric details
    let detailsHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h2 style="margin: 0; color: #667eea;">${formatMetricName(metricName)}</h2>
            <button id="close-metric-modal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
        </div>
        <h4 style="color: #666; margin-bottom: 15px;">${resourceKey}</h4>
        <div style="border-top: 2px solid #667eea; padding-top: 20px;">
    `;
    
    // Display all metric data points
    for (const [key, value] of Object.entries(metricData)) {
        let displayValue = typeof value === 'number' ? value.toFixed(4) : value;
        
        detailsHTML += `
            <div style="margin-bottom: 15px; display: grid; grid-template-columns: 150px 1fr; gap: 10px;">
                <strong style="color: #555;">${key.charAt(0).toUpperCase() + key.slice(1)}:</strong>
                <span style="font-family: monospace; background: #f5f5f5; padding: 5px 10px; border-radius: 4px;">${displayValue}</span>
            </div>
        `;
    }
    
    detailsHTML += `
        </div>
        <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 4px;">
            <p style="margin: 0; font-size: 0.9em; color: #666;">
                <strong>Note:</strong> These values are from the last monitoring period. 
                Select this resource and click "Get Metrics" again to refresh.
            </p>
        </div>
    `;
    
    modalContent.innerHTML = detailsHTML;
    modal.appendChild(modalContent);
    document.body.appendChild(modal);
    
    // Close handlers
    document.getElementById('close-metric-modal').addEventListener('click', () => {
        document.body.removeChild(modal);
    });
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    });
}

function formatMetricName(name) {
    return name
        .replace(/([A-Z])/g, ' $1')
        .replace(/^./, str => str.toUpperCase())
        .trim();
}

async function analyzeCosts() {
    const btn = document.getElementById('cost-btn');
    const results = document.getElementById('cost-results');
    const days = parseInt(document.getElementById('cost-days').value);
    
    const regions = Array.from(document.querySelectorAll('#region-selection input[type="checkbox"]:checked'))
        .map(cb => cb.value);
    
    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span> Analyzing...';
    results.innerHTML = '<p class="status loading">Analyzing costs...</p>';
    
    try {
        const response = await fetch('/api/costs', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({regions, days})
        });
        
        if (!response.ok) throw new Error('Cost analysis failed');
        
        const costs = await response.json();
        displayCosts(costs);
        
    } catch (error) {
        results.innerHTML = `<p class="status error">Error: ${error.message}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = '💰 Analyze Costs';
    }
}

function displayCosts(costs) {
    const container = document.getElementById('cost-results');
    
    if (costs.error) {
        container.innerHTML = `<p class="status error">${costs.error}</p>`;
        return;
    }
    
    container.innerHTML = `
        <div class="cost-summary">
            <h3>Cost Summary (${costs.period.start} to ${costs.period.end})</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0;">
                <div style="background: #667eea; color: white; padding: 20px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 0.9em; opacity: 0.9; margin-bottom: 5px;">Total Cost</div>
                    <div style="font-size: 2em; font-weight: bold;">$${costs.total_cost}</div>
                </div>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 0.9em; color: #666; margin-bottom: 5px;">Daily Average</div>
                    <div style="font-size: 2em; font-weight: bold; color: #667eea;">$${costs.daily_average}</div>
                </div>
            </div>
        </div>
    `;
    
    // Combined breakdown table
    if (costs.by_service && Object.keys(costs.by_service).length > 0) {
        container.innerHTML += '<h4 style="margin-top: 30px;">Cost Breakdown</h4>';
        
        const table = document.createElement('table');
        table.className = 'resource-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Service</th>
                    <th>Region</th>
                    <th style="text-align: right;">Cost</th>
                    <th style="text-align: right;">% of Total</th>
                </tr>
            </thead>
            <tbody></tbody>
        `;
        
        const tbody = table.querySelector('tbody');
        const totalCost = parseFloat(costs.total_cost);
        
        // Create a combined list of all costs by service and region
        const allCosts = [];
        
        // Add by_service costs with breakdown by region if available
        for (const [service, cost] of Object.entries(costs.by_service)) {
            // If we have region breakdown for this service, show it
            let hasRegionBreakdown = false;
            
            if (costs.by_region) {
                for (const [region, regionCost] of Object.entries(costs.by_region)) {
                    // This is a simplified approach - in reality we'd need the API
                    // to return service costs broken down by region
                    // For now, just show service totals
                }
            }
            
            // Show service total
            const percentage = ((parseFloat(cost) / totalCost) * 100).toFixed(1);
            allCosts.push({
                service: service,
                region: 'All Regions',
                cost: parseFloat(cost),
                percentage: percentage
            });
        }
        
        // Sort by cost (highest first)
        allCosts.sort((a, b) => b.cost - a.cost);
        
        // Render rows
        allCosts.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${item.service}</strong></td>
                <td><span class="region-badge">${item.region}</span></td>
                <td style="text-align: right; font-family: monospace;">$${item.cost.toFixed(2)}</td>
                <td style="text-align: right;">
                    <span style="background: #e3f2fd; color: #1976d2; padding: 3px 8px; border-radius: 3px; font-size: 0.9em;">
                        ${item.percentage}%
                    </span>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        container.appendChild(table);
        
        // Add region summary if available
        if (costs.by_region && Object.keys(costs.by_region).length > 1) {
            container.innerHTML += '<h4 style="margin-top: 30px;">Regional Summary</h4>';
            
            const regionTable = document.createElement('table');
            regionTable.className = 'resource-table';
            regionTable.innerHTML = `
                <thead>
                    <tr>
                        <th>Region</th>
                        <th style="text-align: right;">Cost</th>
                        <th style="text-align: right;">% of Total</th>
                    </tr>
                </thead>
                <tbody></tbody>
            `;
            
            const regionTbody = regionTable.querySelector('tbody');
            
            // Sort regions by cost
            const sortedRegions = Object.entries(costs.by_region)
                .map(([region, cost]) => ({
                    region,
                    cost: parseFloat(cost),
                    percentage: ((parseFloat(cost) / totalCost) * 100).toFixed(1)
                }))
                .sort((a, b) => b.cost - a.cost);
            
            sortedRegions.forEach(item => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><span class="region-badge">${item.region}</span></td>
                    <td style="text-align: right; font-family: monospace;">$${item.cost.toFixed(2)}</td>
                    <td style="text-align: right;">
                        <span style="background: #e3f2fd; color: #1976d2; padding: 3px 8px; border-radius: 3px; font-size: 0.9em;">
                            ${item.percentage}%
                        </span>
                    </td>
                `;
                regionTbody.appendChild(row);
            });
            
            container.appendChild(regionTable);
        }
    }
}

async function checkAlerts() {
    if (selectedResources.length === 0) {
        alert('Please select resources first');
        return;
    }
    
    const btn = document.getElementById('alerts-btn');
    const results = document.getElementById('alerts-results');
    
    const thresholds = {
        cpu: parseInt(document.getElementById('threshold-cpu').value),
        memory: parseInt(document.getElementById('threshold-memory').value)
    };
    
    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span> Checking...';
    results.innerHTML = '<p class="status loading">Checking alerts...</p>';
    
    try {
        const response = await fetch('/api/alerts', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({resources: selectedResources, thresholds})
        });
        
        if (!response.ok) throw new Error('Alert check failed');
        
        const alerts = await response.json();
        displayAlerts(alerts);
        
    } catch (error) {
        results.innerHTML = `<p class="status error">Error: ${error.message}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = '⚠️ Check Alerts';
    }
}

function displayAlerts(alerts) {
    const container = document.getElementById('alerts-results');
    
    const totalAlerts = alerts.critical.length + alerts.warning.length + alerts.info.length;
    
    if (totalAlerts === 0) {
        container.innerHTML = '<p class="status success">✅ No alerts found. All resources are healthy!</p>';
        return;
    }
    
    container.innerHTML = `<h3>Alerts Found: ${totalAlerts}</h3>`;
    
    // Critical
    if (alerts.critical.length > 0) {
        container.innerHTML += '<h4>🔴 Critical</h4>';
        alerts.critical.forEach(alert => {
            const div = document.createElement('div');
            div.className = 'alert-item alert-critical';
            div.innerHTML = `
                <strong>${alert.resource_type}:${alert.resource}</strong><br>
                ${alert.message}
            `;
            container.appendChild(div);
        });
    }
    
    // Warning
    if (alerts.warning.length > 0) {
        container.innerHTML += '<h4>⚠️ Warning</h4>';
        alerts.warning.forEach(alert => {
            const div = document.createElement('div');
            div.className = 'alert-item alert-warning';
            div.innerHTML = `
                <strong>${alert.resource_type}:${alert.resource}</strong><br>
                ${alert.message}
            `;
            container.appendChild(div);
        });
    }
    
    // Info
    if (alerts.info.length > 0) {
        container.innerHTML += '<h4>ℹ️ Info</h4>';
        alerts.info.forEach(alert => {
            const div = document.createElement('div');
            div.className = 'alert-item alert-info';
            div.innerHTML = `
                <strong>${alert.resource_type}:${alert.resource_id}</strong><br>
                ${alert.message}
            `;
            container.appendChild(div);
        });
    }
}

async function generateScript() {
    const btn = document.getElementById('generate-script-btn');
    const status = document.getElementById('script-status');
    
    // Get selected regions
    const regions = Array.from(document.querySelectorAll('#region-selection input[type="checkbox"]:checked'))
        .map(cb => cb.value);
    
    if (regions.length === 0) {
        showStatus(status, 'Please select at least one region', 'error');
        return;
    }
    
    // Get resource types
    const resourceTypes = Array.from(document.querySelectorAll('.resource-type-check:checked'))
        .map(cb => cb.value);
    
    if (resourceTypes.length === 0) {
        showStatus(status, 'Please select at least one resource type', 'error');
        return;
    }
    
    // Get checks
    const checks = Array.from(document.querySelectorAll('.check-type:checked'))
        .map(cb => cb.value);
    
    // Get filters
    const filters = {};
    const tagKey = document.getElementById('filter-tag-key').value.trim();
    const tagValue = document.getElementById('filter-tag-value').value.trim();
    if (tagKey && tagValue) {
        filters.tags = {[tagKey]: tagValue};
    }
    const names = document.getElementById('filter-names').value.trim();
    if (names) {
        filters.names = names.split(',').map(s => s.trim());
    }
    const ids = document.getElementById('filter-ids').value.trim();
    if (ids) {
        filters.ids = ids.split(',').map(s => s.trim());
    }
    
    // Get notification
    const email = document.getElementById('notification-email').value.trim();
    
    const config = {
        regions,
        resources: {
            types: resourceTypes,
            filters
        },
        checks,
        thresholds: {
            cpu: parseInt(document.getElementById('threshold-cpu').value),
            memory: parseInt(document.getElementById('threshold-memory').value)
        },
        notification: email ? {email} : {}
    };
    
    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span> Generating...';
    showStatus(status, 'Generating script...', 'loading');
    
    try {
        const response = await fetch('/api/generate-script', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(config)
        });
        
        if (!response.ok) throw new Error('Script generation failed');
        
        const data = await response.json();
        
        if (!data.success || data.error) {
            showStatus(status, `Error: ${data.error || 'Unknown error'}`, 'error');
            return;
        }
        
        // Create blob from script content and download using JavaScript
        // This avoids browser security issues with HTTP file downloads
        const blob = new Blob([data.script], { type: 'text/x-python' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = data.filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        setTimeout(() => {
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        }, 100);
        
        showStatus(status, '✅ Script downloaded! Schedule it with cron or Python scheduler.', 'success');
        
    } catch (error) {
        showStatus(status, `Error: ${error.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '📝 Generate Script';
    }
}

async function loadAllRegions() {
    const btn = document.getElementById('load-more-regions');
    btn.disabled = true;
    btn.textContent = 'Loading...';
    
    try {
        const response = await fetch('/api/regions');
        const data = await response.json();
        
        const container = document.getElementById('region-selection');
        
        // Clear existing except button
        container.querySelectorAll('label').forEach(label => label.remove());
        
        // Add all regions
        data.regions.forEach(region => {
            const label = document.createElement('label');
            const isDefault = ['us-east-1', 'us-west-2'].includes(region);
            label.innerHTML = `<input type="checkbox" value="${region}" ${isDefault ? 'checked' : ''}> ${region}`;
            container.insertBefore(label, btn);
        });
        
        btn.textContent = 'Regions Loaded';
        btn.disabled = true;
        
    } catch (error) {
        btn.textContent = 'Error Loading Regions';
        console.error(error);
    }
}

function showStatus(element, message, type) {
    element.textContent = message;
    element.className = `status ${type}`;
    element.style.display = 'block';
}
