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
    container.innerHTML = '<h3>Resources by Region</h3>';
    
    for (const [region, resourceTypes] of Object.entries(regionsData)) {
        for (const [type, resources] of Object.entries(resourceTypes)) {
            if (resources.length === 0) continue;
            
            const section = document.createElement('div');
            section.style.marginTop = '20px';
            
            const title = document.createElement('h4');
            title.textContent = `${type.toUpperCase()} in ${region}`;
            title.style.color = '#667eea';
            section.appendChild(title);
            
            const table = document.createElement('table');
            table.className = 'resource-table';
            
            // Table header
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            headerRow.innerHTML = `
                <th><input type="checkbox" class="select-all" data-type="${type}" data-region="${region}"></th>
                <th>Name/ID</th>
                <th>Type/Class</th>
                <th>State/Status</th>
                <th>Details</th>
            `;
            thead.appendChild(headerRow);
            table.appendChild(thead);
            
            // Table body
            const tbody = document.createElement('tbody');
            resources.forEach(resource => {
                const row = document.createElement('tr');
                const resourceId = resource.id || resource.name;
                
                row.innerHTML = `
                    <td><input type="checkbox" class="resource-checkbox" data-type="${type}" data-id="${resourceId}" data-region="${region}"></td>
                    <td>${resource.name || resource.id || 'N/A'}</td>
                    <td>${resource.type || resource.class || resource.engine || resource.runtime || 'N/A'}</td>
                    <td><span class="badge badge-${(resource.state || resource.status || '').toLowerCase()}">${resource.state || resource.status || 'N/A'}</span></td>
                    <td>${getResourceDetails(type, resource)}</td>
                `;
                tbody.appendChild(row);
            });
            table.appendChild(tbody);
            
            section.appendChild(table);
            container.appendChild(section);
        }
    }
    
    // Add select-all handlers
    document.querySelectorAll('.select-all').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const type = e.target.dataset.type;
            const region = e.target.dataset.region;
            const checkboxes = document.querySelectorAll(`.resource-checkbox[data-type="${type}"][data-region="${region}"]`);
            checkboxes.forEach(cb => cb.checked = e.target.checked);
        });
    });
    
    // Track selected resources
    document.querySelectorAll('.resource-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedResources);
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
                `;
                grid.appendChild(item);
            }
        }
        
        card.appendChild(grid);
        container.appendChild(card);
    }
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
