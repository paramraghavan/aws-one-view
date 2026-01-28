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
    showStatus(status, 'Scanning regions for resources...', 'loading');
    
    try {
        const response = await fetch('/api/discover', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({regions, filters})
        });
        
        if (!response.ok) throw new Error('Discovery failed');
        
        discoveredResources = await response.json();
        
        // Display results
        displayResourceSummary(discoveredResources.summary);
        displayResourceList(discoveredResources.regions);
        
        showStatus(status, `Found ${Object.values(discoveredResources.summary).reduce((a, b) => a + b, 0)} resources`, 'success');
        
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
    container.innerHTML = '<h3>Resources by Type</h3>';
    
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
        
        const headerText = document.createElement('div');
        headerText.innerHTML = `
            <strong>${type.toUpperCase()}</strong>
            <span style="margin-left: 10px; color: #666;">${resources.length} resources</span>
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
        
        // Create table
        const table = document.createElement('table');
        table.className = 'resource-table';
        
        // Table header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        headerRow.innerHTML = `
            <th><input type="checkbox" class="select-all" data-type="${type}"></th>
            <th>Name/ID</th>
            <th>Type/Class</th>
            <th>State/Status</th>
            <th>Region</th>
            <th>Details</th>
            <th>Actions</th>
        `;
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Table body
        const tbody = document.createElement('tbody');
        resources.forEach(resource => {
            const row = document.createElement('tr');
            const resourceId = resource.id || resource.name;
            const region = resource._region;
            
            row.innerHTML = `
                <td><input type="checkbox" class="resource-checkbox" data-type="${type}" data-id="${resourceId}" data-region="${region}"></td>
                <td>${resource.name || resource.id || 'N/A'}</td>
                <td>${resource.type || resource.class || resource.engine || resource.runtime || 'N/A'}</td>
                <td><span class="badge badge-${(resource.state || resource.status || '').toLowerCase()}">${resource.state || resource.status || 'N/A'}</span></td>
                <td>${region}</td>
                <td>${getResourceDetails(type, resource)}</td>
                <td><button class="details-btn" data-type="${type}" data-id="${resourceId}" data-region="${region}">Details</button></td>
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
                item.style.cursor = 'pointer';
                item.style.transition = 'transform 0.2s, box-shadow 0.2s';
                
                let value = metricData.current || metricData.total || metricData.avg || 0;
                value = typeof value === 'number' ? value.toFixed(2) : value;
                
                item.innerHTML = `
                    <div class="label">${formatMetricName(metricName)}</div>
                    <div class="value">${value}</div>
                    <div style="font-size: 0.8em; color: #999; margin-top: 5px;">Click for details</div>
                `;
                
                // Add hover effect
                item.addEventListener('mouseenter', () => {
                    item.style.transform = 'translateY(-2px)';
                    item.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
                });
                
                item.addEventListener('mouseleave', () => {
                    item.style.transform = 'translateY(0)';
                    item.style.boxShadow = 'none';
                });
                
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
            <h3>Cost Summary</h3>
            <div class="cost-number">$${costs.total_cost}</div>
            <p>Period: ${costs.period.start} to ${costs.period.end}</p>
            <p>Daily Average: $${costs.daily_average}</p>
        </div>
    `;
    
    // Top services
    if (costs.by_service && Object.keys(costs.by_service).length > 0) {
        container.innerHTML += '<h4>Top Services by Cost</h4>';
        const table = document.createElement('table');
        table.className = 'resource-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Service</th>
                    <th>Cost</th>
                </tr>
            </thead>
            <tbody>
                ${Object.entries(costs.by_service).map(([service, cost]) => `
                    <tr>
                        <td>${service}</td>
                        <td>$${cost}</td>
                    </tr>
                `).join('')}
            </tbody>
        `;
        container.appendChild(table);
    }
    
    // By region
    if (costs.by_region && Object.keys(costs.by_region).length > 0) {
        container.innerHTML += '<h4 style="margin-top:20px">Cost by Region</h4>';
        const table = document.createElement('table');
        table.className = 'resource-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Region</th>
                    <th>Cost</th>
                </tr>
            </thead>
            <tbody>
                ${Object.entries(costs.by_region).map(([region, cost]) => `
                    <tr>
                        <td>${region}</td>
                        <td>$${cost}</td>
                    </tr>
                `).join('')}
            </tbody>
        `;
        container.appendChild(table);
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
        
        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'aws_monitor_job.py';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
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
