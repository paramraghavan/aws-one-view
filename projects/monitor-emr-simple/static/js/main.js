// EMR Monitoring Tool JavaScript

let currentCluster = '';
let viewMode = 'spark';
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
            option.textContent = `${cluster.name} - ${cluster.description}`;
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
        updateClusterStats(info);
        updateResourceUsage(info);
    } catch (error) {
        console.error('Error loading cluster info:', error);
        showError('Failed to load cluster information');
    }
}

function updateClusterStats(info) {
    const statsContainer = document.getElementById('clusterStats');

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

    statsContainer.innerHTML = stats.map(stat => `
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

        const response = await fetch(`/api/cluster/${currentCluster}/applications?source=${viewMode}`);
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

function updateApplicationsTable(applications) {
    const tbody = document.getElementById('applicationsBody');

    if (!applications || applications.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No applications found</td></tr>';
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
        const appId = app.id || app.applicationId || 'N/A';

        return `
            <tr>
                <td title="${appId}">
                    <span class="status-indicator ${status.toLowerCase()}"></span>
                    ${appId.length > 20 ? appId.substring(0, 20) + '...' : appId}
                </td>
                <td title="${app.name || 'N/A'}">${app.name ? (app.name.length > 30 ? app.name.substring(0, 30) + '...' : app.name) : 'N/A'}</td>
                <td><span class="status-badge status-${status.toLowerCase()}">${status}</span></td>
                <td>${duration}</td>
                <td>${resources}</td>
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

function getApplicationStatus(app) {
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
    if (app.total_cores && app.total_memory_mb) {
        return `${app.total_cores} cores, ${formatMemory(app.total_memory_mb * 1024 * 1024)}`;
    } else if (app.allocatedMB && app.allocatedVCores) {
        return `${app.allocatedVCores} cores, ${formatMemory(app.allocatedMB * 1024 * 1024)}`;
    }
    return 'N/A';
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

    // Update button text
    const btn = document.querySelector('[onclick="toggleView()"]');
    btn.textContent = viewMode === 'spark' ? 'Switch to YARN' : 'Switch to Spark';

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