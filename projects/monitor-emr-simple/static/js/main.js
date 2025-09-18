// EMR Monitoring Tool JavaScript

let currentCluster = '';
let viewMode = 'spark';
let statusFilter = 'all';
let refreshInterval;
let isRefreshing = false;

// Initialize the application
async function init() {
    try {
        showLoading('Initializing...');
        const response = await fetch('/api/clusters');
        const clusters = await response.json();

        const select = document.getElementById('clusterSelect');
        select.innerHTML = '<option value="">Choose a cluster...</option>';

        for (const [id, cluster] of Object.entries(clusters)) {
            const option = document.createElement('option');
            option.value = id;
            const clusterIdText = cluster.aws_cluster_id ? ` (${cluster.aws_cluster_id})` : '';
            option.textContent = `${cluster.name}${clusterIdText} - ${cluster.description}`;
            select.appendChild(option);
        }

        hideLoading();
    } catch (error) {
        console.error('Error loading clusters:', error);
        showError('Failed to load clusters. Please check your configuration.');
    }
}

function selectCluster() {
    const select = document.getElementById('clusterSelect');
    currentCluster = select.value;

    if (currentCluster) {
        document.getElementById('dashboard').style.display = 'grid';
        refreshData();
        startAutoRefresh();
    } else {
        document.getElementById('dashboard').style.display = 'none';
        stopAutoRefresh();
    }
}

async function refreshData() {
    if (!currentCluster || isRefreshing) return;

    isRefreshing = true;
    const refreshBtn = document.querySelector('.refresh-btn');
    refreshBtn.classList.add('spinning');

    try {
        await Promise.all([
            loadClusterInfo(),
            loadApplications()
        ]);
    } catch (error) {
        console.error('Error refreshing data:', error);
        showError('Failed to refresh data');
    } finally {
        isRefreshing = false;
        refreshBtn.classList.remove('spinning');
    }
}

async function loadClusterInfo() {
    try {
        const response = await fetch(`/api/cluster/${currentCluster}/info`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const info = await response.json();

        // Get cluster config for additional details
        const clustersResponse = await fetch('/api/clusters');
        const clusters = await clustersResponse.json();
        const clusterConfig = clusters[currentCluster] || {};

        // Add cluster config info to the cluster info
        info.clusterConfig = clusterConfig;

        updateClusterStats(info);
        updateResourceUsage(info);
        updateTaskNodesInfo(info);
        updateSpotAnalysis(info);
    } catch (error) {
        console.error('Error loading cluster info:', error);
        showError('Failed to load cluster information');
    }
}

function updateTaskNodesInfo(info) {
    const container = document.getElementById('taskNodesInfo');

    const taskNodes = info.taskNodes || [];
    const instanceTypes = info.instanceTypes || {};
    const nodeStates = info.nodeStates || {};

    if (taskNodes.length === 0) {
        container.innerHTML = '<div class="text-center">No task node information available</div>';
        return;
    }

    // Summary stats
    const totalNodes = taskNodes.length;
    const spotNodes = instanceTypes.spot || 0;
    const onDemandNodes = instanceTypes['on-demand'] || 0;
    const unhealthyNodes = (nodeStates.LOST || 0) + (nodeStates.UNHEALTHY || 0) + (nodeStates.DECOMMISSIONED || 0);

    container.innerHTML = `
        <div class="stats-grid" style="margin-bottom: 20px;">
            <div class="stat-item">
                <div class="stat-value">🖥️ ${totalNodes}</div>
                <div class="stat-label">Total Nodes</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">⚡ ${spotNodes}</div>
                <div class="stat-label">Spot Instances</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">💎 ${onDemandNodes}</div>
                <div class="stat-label">On-Demand</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">⚠️ ${unhealthyNodes}</div>
                <div class="stat-label">Unhealthy</div>
            </div>
        </div>

        <details>
            <summary style="cursor: pointer; font-weight: bold; margin-bottom: 10px;">📋 View All Task Nodes (${totalNodes})</summary>
            <div class="task-nodes-table-container" style="max-height: 300px; overflow-y: auto;">
                <table class="applications-table">
                    <thead>
                        <tr>
                            <th>Node ID</th>
                            <th>State</th>
                            <th>Type</th>
                            <th>Health</th>
                            <th>Risk</th>
                            <th>Resources</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${taskNodes.map(node => `
                            <tr>
                                <td title="${node.node_id}">${node.node_id.length > 20 ? node.node_id.substring(0, 20) + '...' : node.node_id}</td>
                                <td><span class="status-badge status-${node.state.toLowerCase()}">${node.state}</span></td>
                                <td>${getInstanceTypeIcon(node.instance_type)} ${node.instance_type}</td>
                                <td><span class="health-indicator ${node.health_status}">${getHealthIcon(node.health_status)}</span></td>
                                <td><span class="risk-indicator ${node.spot_termination_risk}">${getRiskIcon(node.spot_termination_risk)}</span></td>
                                <td>${formatMemory(node.memory_mb * 1024 * 1024)} / ${node.vcores} cores</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </details>
    `;
}

function updateSpotAnalysis(info) {
    const container = document.getElementById('spotAnalysis');

    // Load spot analysis data
    loadSpotAnalysisData();
}

async function loadSpotAnalysisData() {
    try {
        const response = await fetch(`/api/cluster/${currentCluster}/spot-analysis`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const analysis = await response.json();
        const container = document.getElementById('spotAnalysis');

        const totalSpot = analysis.total_spot_nodes || 0;
        const highRisk = analysis.high_risk_nodes || 0;
        const mediumRisk = analysis.medium_risk_nodes || 0;
        const lowRisk = analysis.low_risk_nodes || 0;
        const unhealthy = analysis.unhealthy_nodes || 0;

        if (totalSpot === 0) {
            container.innerHTML = '<div class="text-center">No spot instances detected</div>';
            return;
        }

        const riskPercentage = totalSpot > 0 ? ((highRisk + mediumRisk) / totalSpot * 100) : 0;
        const riskClass = riskPercentage > 50 ? 'danger' : riskPercentage > 25 ? 'warning' : '';

        container.innerHTML = `
            <div class="stats-grid" style="margin-bottom: 20px;">
                <div class="stat-item">
                    <div class="stat-value">⚡ ${totalSpot}</div>
                    <div class="stat-label">Spot Instances</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">🔴 ${highRisk}</div>
                    <div class="stat-label">High Risk</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">🟡 ${mediumRisk}</div>
                    <div class="stat-label">Medium Risk</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">🟢 ${lowRisk}</div>
                    <div class="stat-label">Low Risk</div>
                </div>
            </div>

            <div style="margin-bottom: 15px;">
                <h4>⚠️ Termination Risk Assessment</h4>
                <div>Risk Level: ${riskPercentage.toFixed(1)}% of spot instances at risk</div>
                <div class="resource-bar ${riskClass}" style="margin-top: 10px;">
                    <div class="resource-fill" style="width: ${riskPercentage}%"></div>
                </div>
            </div>

            ${unhealthy > 0 ? `
                <div class="error" style="margin-top: 10px;">
                    ⚠️ ${unhealthy} spot instance(s) currently unhealthy or terminated
                </div>
            ` : ''}

            <div style="margin-top: 15px; font-size: 14px; color: #666;">
                💡 Tip: Monitor high-risk spot instances closely. Consider using mixed instance types for critical workloads.
            </div>
        `;

    } catch (error) {
        console.error('Error loading spot analysis:', error);
        document.getElementById('spotAnalysis').innerHTML =
            '<div class="error">Error loading spot instance analysis</div>';
    }
}

function getInstanceTypeIcon(type) {
    switch(type) {
        case 'spot': return '⚡';
        case 'on-demand': return '💎';
        case 'reserved': return '🔒';
        default: return '❓';
    }
}

function getHealthIcon(health) {
    switch(health) {
        case 'healthy': return '🟢';
        case 'stale': return '🟡';
        case 'unknown': return '🔴';
        default: return '❓';
    }
}

function getRiskIcon(risk) {
    switch(risk) {
        case 'low': return '🟢';
        case 'medium': return '🟡';
        case 'high': return '🔴';
        default: return '❓';
    }
}

async function refreshTaskNodes() {
    try {
        const refreshBtn = document.querySelector('[onclick="refreshTaskNodes()"]');
        refreshBtn.classList.add('spinning');

        await loadClusterInfo();

        refreshBtn.classList.remove('spinning');
    } catch (error) {
        console.error('Error refreshing task nodes:', error);
    }
}

function updateClusterStats(info) {
    const statsContainer = document.getElementById('clusterStats');

    // Add cluster info header
    let clusterHeader = '';
    if (info.clusterConfig || info.awsClusterId) {
        const config = info.clusterConfig || {};
        const awsId = info.awsClusterId || config.aws_cluster_id || 'Not Available';

        clusterHeader = `
            <div class="cluster-info-header" style="grid-column: 1 / -1; margin-bottom: 15px; padding: 15px; background: #e3f2fd; border-radius: 6px; border-left: 4px solid #2196f3;">
                <h4 style="margin: 0 0 5px 0; color: #1976d2;">🏷️ ${config.name || 'EMR Cluster'}</h4>
                <div style="font-weight: bold; color: #1976d2; margin-bottom: 5px;">AWS Cluster ID: <span style="font-family: monospace; background: #fff; padding: 2px 6px; border-radius: 3px;">${awsId}</span></div>
                ${config.description ? `<div style="font-size: 14px; color: #666;">${config.description}</div>` : ''}
            </div>
        `;
    }

    const stats = [
        {
            label: 'Total Nodes',
            value: info.totalNodes || 0,
            icon: '🖥️'
        },
        {
            label: 'Running Apps',
            value: info.appsRunning || 0,
            icon: '🏃'
        },
        {
            label: 'Pending Apps',
            value: info.appsPending || 0,
            icon: '⏳'
        },
        {
            label: 'Available Memory',
            value: formatMemory((info.availableMB || 0) * 1024 * 1024),
            icon: '💾'
        }
    ];

    statsContainer.innerHTML = clusterHeader + stats.map(stat => `
        <div class="stat-item">
            <div class="stat-value">${stat.icon} ${stat.value}</div>
            <div class="stat-label">${stat.label}</div>
        </div>
    `).join('');
}

function updateResourceUsage(info) {
    const container = document.getElementById('resourceUsage');

    const totalMemory = (info.totalMB || 0);
    const usedMemory = totalMemory - (info.availableMB || 0);
    const memoryPercent = totalMemory > 0 ? (usedMemory / totalMemory) * 100 : 0;

    const totalCores = (info.totalVirtualCores || 0);
    const usedCores = totalCores - (info.availableVirtualCores || 0);
    const coresPercent = totalCores > 0 ? (usedCores / totalCores) * 100 : 0;

    // Determine warning levels
    const memoryClass = memoryPercent > 90 ? 'danger' : memoryPercent > 75 ? 'warning' : '';
    const coresClass = coresPercent > 90 ? 'danger' : coresPercent > 75 ? 'warning' : '';

    container.innerHTML = `
        <div style="margin-bottom: 20px;">
            <h4>💾 Memory Usage</h4>
            <div>Used: ${formatMemory(usedMemory * 1024 * 1024)} / ${formatMemory(totalMemory * 1024 * 1024)} (${memoryPercent.toFixed(1)}%)</div>
            <div class="resource-bar ${memoryClass}">
                <div class="resource-fill" style="width: ${memoryPercent}%"></div>
            </div>
        </div>
        <div>
            <h4>⚡ CPU Usage</h4>
            <div>Used: ${usedCores} / ${totalCores} cores (${coresPercent.toFixed(1)}%)</div>
            <div class="resource-bar ${coresClass}">
                <div class="resource-fill" style="width: ${coresPercent}%"></div>
            </div>
        </div>
    `;
}

async function loadApplications() {
    try {
        document.getElementById('applicationsLoading').style.display = 'block';
        document.getElementById('applicationsContent').style.display = 'none';

        const response = await fetch(`/api/cluster/${currentCluster}/applications?source=${viewMode}&status=${statusFilter}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const applications = await response.json();
        updateApplicationsTable(applications);

        document.getElementById('applicationsLoading').style.display = 'none';
        document.getElementById('applicationsContent').style.display = 'block';
    } catch (error) {
        console.error('Error loading applications:', error);
        document.getElementById('applicationsLoading').innerHTML =
            '<div class="error">❌ Error loading applications</div>';
    }
}

function filterApplications() {
    const filterSelect = document.getElementById('statusFilter');
    statusFilter = filterSelect.value;

    if (currentCluster) {
        loadApplications();
    }
}

function updateApplicationsTable(applications) {
    const tbody = document.getElementById('applicationsBody');

    if (!applications || applications.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No applications found</td></tr>';
        return;
    }

    // Sort applications by start time (most recent first)
    applications.sort((a, b) => {
        const timeA = a.startedTime || a.startTime || 0;
        const timeB = b.startedTime || b.startTime || 0;
        return timeB - timeA;
    });

    tbody.innerHTML = applications.map(app => {
        const status = getApplicationStatus(app);
        const duration = getApplicationDuration(app);
        const resources = getApplicationResources(app);
        const efficiency = getApplicationEfficiency(app);
        const appId = app.id || app.applicationId || 'N/A';

        // Add source indicator
        const sourceIcon = app.source === 'spark' ? '📊' : '🎯';
        const sourceTitle = app.source === 'spark' ? 'Spark History Server' : 'YARN ResourceManager';

        return `
            <tr>
                <td title="${appId}">
                    <span class="status-indicator ${status.toLowerCase()}"></span>
                    ${appId.length > 20 ? appId.substring(0, 20) + '...' : appId}
                    <span style="opacity: 0.6; margin-left: 5px;" title="${sourceTitle}">${sourceIcon}</span>
                </td>
                <td title="${app.name || 'N/A'}">${app.name ? (app.name.length > 30 ? app.name.substring(0, 30) + '...' : app.name) : 'N/A'}</td>
                <td><span class="status-badge status-${status.toLowerCase()}">${status}</span></td>
                <td>${duration}</td>
                <td>${resources}</td>
                <td>${efficiency}</td>
                <td>
                    <button class="btn btn-small" onclick="viewDetails('${appId}')" title="View Details">
                        📊
                    </button>
                    <button class="btn btn-small btn-secondary" onclick="viewLogs('${appId}')" title="View Logs">
                        📋
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function getApplicationEfficiency(app) {
    if (app.source === 'yarn' && app.standardized_status === 'RUNNING') {
        // For running YARN applications, show real-time efficiency
        const memEff = app.memory_efficiency_percent || 0;
        const vcoreEff = app.vcore_efficiency_percent || 0;

        if (memEff > 0 || vcoreEff > 0) {
            const avgEff = (memEff + vcoreEff) / 2;
            let effIcon = '🔴'; // Low efficiency
            if (avgEff > 75) effIcon = '🟢'; // Good efficiency
            else if (avgEff > 50) effIcon = '🟡'; // Medium efficiency

            return `${effIcon} ${avgEff.toFixed(0)}%`;
        }
    }

    // For completed applications, show resource hours
    if (app.memory_hours || app.vcore_hours) {
        const memHours = (app.memory_hours || 0).toFixed(1);
        const vcoreHours = (app.vcore_hours || 0).toFixed(1);
        return `${memHours}h mem, ${vcoreHours}h cpu`;
    }

    return 'N/A';
}

function getApplicationStatus(app) {
    // Use standardized status if available, otherwise fallback to source-specific logic
    if (app.standardized_status) {
        return app.standardized_status;
    }

    // Fallback logic for older data
    if (app.source === 'spark') {
        const lastAttempt = app.attempts ? app.attempts[app.attempts.length - 1] : {};
        return lastAttempt.completed === false ? 'RUNNING' : 'SUCCEEDED';
    } else {
        return app.finalStatus || app.state || 'UNKNOWN';
    }
}

function getApplicationDuration(app) {
    if (app.source === 'spark') {
        const lastAttempt = app.attempts ? app.attempts[app.attempts.length - 1] : {};
        if (lastAttempt.startTime && lastAttempt.endTime) {
            const duration = new Date(lastAttempt.endTime) - new Date(lastAttempt.startTime);
            return formatDuration(duration);
        } else if (lastAttempt.startTime && !lastAttempt.endTime) {
            const duration = Date.now() - new Date(lastAttempt.startTime);
            return formatDuration(duration) + ' (running)';
        }
        return 'N/A';
    } else {
        return app.durationFormatted || 'N/A';
    }
}

function getApplicationResources(app) {
    if (app.source === 'spark') {
        // Enhanced Spark History Server data
        if (app.memory_gb && app.total_cores) {
            return `${app.total_cores} cores, ${formatMemory(app.memory_gb * 1024 * 1024 * 1024)}`;
        } else if (app.total_cores && app.total_memory_mb) {
            return `${app.total_cores} cores, ${formatMemory(app.total_memory_mb * 1024 * 1024)}`;
        }
        return 'N/A (History Server)';
    } else {
        // Enhanced YARN ResourceManager data
        const allocated_mb = app.allocatedMB || 0;
        const allocated_vcores = app.allocatedVCores || 0;
        const running_containers = app.runningContainers || 0;

        let resourceText = '';
        if (allocated_vcores > 0 && allocated_mb > 0) {
            resourceText = `${allocated_vcores} cores, ${formatMemory(allocated_mb * 1024 * 1024)}`;
            if (running_containers > 0) {
                resourceText += ` (${running_containers} containers)`;
            }
        } else {
            resourceText = 'N/A';
        }

        return resourceText;
    }
}

async function showApplicationSummary() {
    try {
        const modal = document.getElementById('detailsModal');
        const modalBody = document.getElementById('modalBody');

        // Show loading
        document.querySelector('.modal-header h2').textContent = 'Application Summary by Name';
        modalBody.innerHTML = '<div class="loading">Loading application summary...</div>';
        modal.style.display = 'block';

        // Fetch summary data
        const response = await fetch(`/api/cluster/${currentCluster}/application-summary?hours=24`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const summary = await response.json();

        if (!summary || summary.length === 0) {
            modalBody.innerHTML = '<div class="text-center">No application summary available</div>';
            return;
        }

        // Create summary table
        modalBody.innerHTML = `
            <div style="margin-bottom: 20px;">
                <h4>📊 Application Summary (Last 24 Hours)</h4>
                <p>Grouped by application name showing resource usage patterns</p>
            </div>

            <div style="max-height: 60vh; overflow-y: auto;">
                <table class="applications-table">
                    <thead>
                        <tr>
                            <th>Application Name</th>
                            <th>Total Runs</th>
                            <th>Success Rate</th>
                            <th>Memory-Hours</th>
                            <th>vCore-Hours</th>
                            <th>Avg Duration</th>
                            <th>Users</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${summary.map(app => `
                            <tr>
                                <td title="${app.app_name}">${app.app_name.length > 30 ? app.app_name.substring(0, 30) + '...' : app.app_name}</td>
                                <td>
                                    <span style="color: #2196f3;">${app.running || 0} running</span> /
                                    <span style="color: #4caf50;">${app.succeeded || 0} success</span> /
                                    <span style="color: #f44336;">${app.failed || 0} failed</span>
                                    <br><strong>Total: ${app.total_runs}</strong>
                                </td>
                                <td>
                                    <span class="status-badge ${app.success_rate >= 90 ? 'status-succeeded' : app.success_rate >= 70 ? 'status-accepted' : 'status-failed'}">
                                        ${app.success_rate.toFixed(1)}%
                                    </span>
                                </td>
                                <td>${app.total_memory_hours.toFixed(1)}</td>
                                <td>${app.total_vcore_hours.toFixed(1)}</td>
                                <td>${app.avg_duration_minutes.toFixed(1)} min</td>
                                <td title="${app.users}">${app.users.length > 20 ? app.users.substring(0, 20) + '...' : app.users}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>

            <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 6px;">
                <h5>💡 Insights</h5>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li><strong>High Memory-Hours:</strong> Look for applications that might benefit from optimization</li>
                    <li><strong>Low Success Rates:</strong> Applications that frequently fail may need attention</li>
                    <li><strong>Many Runs:</strong> Frequently executed applications should be optimized for efficiency</li>
                    <li><strong>Long Durations:</strong> Applications taking too long might need performance tuning</li>
                </ul>
            </div>
        `;

    } catch (error) {
        console.error('Error loading application summary:', error);
        document.getElementById('modalBody').innerHTML =
            '<div class="error">❌ Error loading application summary</div>';
    }
}

async function viewDetails(appId) {
    try {
        showModal('Loading application details...', '⏳ Loading...');

        const response = await fetch(`/api/cluster/${currentCluster}/application/${appId}/details`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const details = await response.json();

        const modalBody = document.getElementById('modalBody');
        modalBody.innerHTML = `
            <h3>📊 Application: ${appId}</h3>
            <div class="mt-10">
                <h4>Resource Summary:</h4>
                <ul>
                    <li><strong>Executors:</strong> ${details.executor_count || 'N/A'}</li>
                    <li><strong>Total Cores:</strong> ${details.total_cores || 'N/A'}</li>
                    <li><strong>Total Memory:</strong> ${details.total_memory_mb ? formatMemory(details.total_memory_mb * 1024 * 1024) : 'N/A'}</li>
                </ul>
            </div>
            <div class="mt-10">
                <h4>Raw Data:</h4>
                <pre>${JSON.stringify(details, null, 2)}</pre>
            </div>
        `;

        document.querySelector('.modal-header h2').textContent = 'Application Details';

    } catch (error) {
        console.error('Error loading application details:', error);
        showModal('❌ Error loading application details', 'Failed to load details');
    }
}

async function viewLogs(appId) {
    try {
        showModal('Loading application logs...', '⏳ Loading...');

        const response = await fetch(`/api/cluster/${currentCluster}/application/${appId}/logs`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();

        const modalBody = document.getElementById('modalBody');
        modalBody.innerHTML = `
            <h3>📋 Logs for Application: ${appId}</h3>
            <pre>${data.logs}</pre>
        `;

        document.querySelector('.modal-header h2').textContent = 'Application Logs';

    } catch (error) {
        console.error('Error loading application logs:', error);
        showModal('❌ Error loading application logs', 'Failed to load logs');
    }
}

function showModal(title, content) {
    document.querySelector('.modal-header h2').textContent = title;
    document.getElementById('modalBody').innerHTML = `<div class="p-10">${content}</div>`;
    document.getElementById('detailsModal').style.display = 'block';
}

function closeModal() {
    document.getElementById('detailsModal').style.display = 'none';
}

function toggleView() {
    viewMode = viewMode === 'spark' ? 'yarn' : 'spark';

    // Update button text with more descriptive labels
    const btn = document.querySelector('[onclick="toggleView()"]');
    if (viewMode === 'spark') {
        btn.textContent = 'Switch to YARN (Live)';
        btn.title = 'Switch to YARN ResourceManager - better for running applications';
    } else {
        btn.textContent = 'Switch to Spark (History)';
        btn.title = 'Switch to Spark History Server - better for completed applications';
    }

    if (currentCluster) {
        loadApplications();
    }
}

function formatMemory(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatDuration(ms) {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) {
        return `${days}d ${hours % 24}h`;
    } else if (hours > 0) {
        return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
        return `${minutes}m ${seconds % 60}s`;
    } else {
        return `${seconds}s`;
    }
}

function startAutoRefresh() {
    stopAutoRefresh();
    refreshInterval = setInterval(refreshData, 30000); // Refresh every 30 seconds
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

function showLoading(message = 'Loading...') {
    // Could implement a global loading indicator here
    console.log(message);
}

function hideLoading() {
    // Hide global loading indicator
    console.log('Loading complete');
}

function showError(message) {
    // Could implement a toast notification system here
    console.error(message);
    alert(message); // Simple fallback
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('detailsModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Escape key closes modal
    if (event.key === 'Escape') {
        closeModal();
    }

    // Ctrl/Cmd + R refreshes data
    if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
        event.preventDefault();
        refreshData();
    }
});

// Initialize the application when page loads
document.addEventListener('DOMContentLoaded', init);

// Handle page visibility changes (pause/resume auto-refresh)
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        stopAutoRefresh();
    } else if (currentCluster) {
        startAutoRefresh();
        refreshData(); // Refresh immediately when page becomes visible
    }
});