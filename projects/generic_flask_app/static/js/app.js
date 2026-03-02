let socket = null;
let currentExecutionId = null;
let selectedFiles = [];
let currentBrowserPath = null;
let selectedBrowserFiles = new Set();

document.addEventListener('DOMContentLoaded', () => {
    initializeSocket();
    loadEnvironments();
    loadQuickLocations();
    setupEventListeners();
});

function initializeSocket() {
    socket = io();
    socket.on('output', (data) => {
        addOutputLine(data.data);
    });
    socket.on('complete', (data) => {
        onExecutionComplete(data.status);
    });
}

async function loadEnvironments() {
    try {
        const response = await fetch('/api/environments');
        const environments = await response.json();

        const select = document.getElementById('environment');
        environments.forEach(env => {
            const option = document.createElement('option');
            option.value = env;
            option.textContent = env.toUpperCase();
            select.appendChild(option);
        });

        // Auto-load default or first environment
        const saved = localStorage.getItem('default_env');
        if (saved && environments.includes(saved)) {
            select.value = saved;
        } else if (environments.length > 0) {
            select.value = environments[0];
        }

        loadEnvironmentSettings();
    } catch (error) {
        console.error('Error loading environments:', error);
    }
}

async function loadQuickLocations() {
    try {
        const response = await fetch('/api/quick-locations');
        const result = await response.json();

        if (result.success && result.locations.length > 0) {
            const quickDiv = document.getElementById('quick-locations');
            quickDiv.innerHTML = '<strong>Quick Access:</strong> ';

            result.locations.forEach(loc => {
                const btn = document.createElement('button');
                btn.className = 'btn btn-sm';
                btn.textContent = loc.name;
                btn.type = 'button';
                btn.onclick = () => loadDirectory(loc.path);
                quickDiv.appendChild(btn);
            });
        }
    } catch (error) {
        console.error('Error loading quick locations:', error);
    }
}

function setupEventListeners() {
    const passwordInput = document.getElementById('password');
    const directoryInput = document.getElementById('directory-path');

    document.getElementById('environment').addEventListener('change', () => {
        loadEnvironmentSettings();
    });

    document.getElementById('set-default').addEventListener('change', (e) => {
        const env = document.getElementById('environment').value;
        if (e.target.checked && env) {
            localStorage.setItem('default_env', env);
        } else {
            localStorage.removeItem('default_env');
        }
    });

    // Auto-save password to localStorage when user types
    passwordInput.addEventListener('input', () => {
        const env = document.getElementById('environment').value;
        const password = passwordInput.value;
        if (env && password) {
            localStorage.setItem(`password_${env}`, password);
            document.getElementById('cached-msg').style.display = 'block';
        }
    });

    // Auto-save directory path to localStorage when user types or browses
    directoryInput.addEventListener('change', () => {
        const env = document.getElementById('environment').value;
        const path = directoryInput.value;
        if (env && path) {
            localStorage.setItem(`directory_${env}`, path);
        }
    });

    document.getElementById('browse-btn').addEventListener('click', openFileBrowser);
    document.getElementById('browser-back').addEventListener('click', browserGoBack);
    document.getElementById('browser-close').addEventListener('click', closeFileBrowser);
    document.getElementById('browser-select').addEventListener('click', selectBrowserFiles);

    document.getElementById('ingest-btn').addEventListener('click', startIngest);
    document.getElementById('stop-btn').addEventListener('click', stopExecution);
    document.getElementById('clear-btn').addEventListener('click', clearOutput);
}

function loadEnvironmentSettings() {
    const env = document.getElementById('environment').value;

    if (!env) {
        document.getElementById('password').value = '';
        document.getElementById('directory-path').value = '';
        document.getElementById('cached-msg').style.display = 'none';
        return;
    }

    // Load password from localStorage
    const savedPassword = localStorage.getItem(`password_${env}`);
    if (savedPassword) {
        document.getElementById('password').value = savedPassword;
        document.getElementById('cached-msg').style.display = 'block';
    } else {
        document.getElementById('password').value = '';
        document.getElementById('cached-msg').style.display = 'none';
    }

    // Load directory path from localStorage
    const savedPath = localStorage.getItem(`directory_${env}`);
    if (savedPath) {
        document.getElementById('directory-path').value = savedPath;
    } else {
        document.getElementById('directory-path').value = '';
    }
}

function updateFileList() {
    const container = document.getElementById('file-list');
    container.innerHTML = '';

    if (selectedFiles.length === 0) {
        container.innerHTML = '<p style="color: #999;">No files selected</p>';
        return;
    }

    selectedFiles.forEach(filePath => {
        const div = document.createElement('div');
        div.className = 'file-item';
        div.innerHTML = `📄 <strong>${getFileName(filePath)}</strong><br><small style="color: #666;">${filePath}</small>`;
        container.appendChild(div);
    });
}

function getFileName(fullPath) {
    return fullPath.split(/[\/\\]/).pop();
}

async function startIngest() {
    const env = document.getElementById('environment').value;
    let password = document.getElementById('password').value;

    if (!env) {
        alert('Please select an environment');
        return;
    }

    if (!password || password === '(cached)') {
        alert('Please enter a password');
        return;
    }

    if (selectedFiles.length === 0) {
        alert('Please select files using the Browse button');
        return;
    }

    try {
        document.getElementById('ingest-btn').disabled = true;
        document.getElementById('stop-btn').style.display = 'inline-block';
        updateStatus('running', 'Running...');
        clearOutput();

        const response = await fetch('/api/ingest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                password: password,
                files: selectedFiles,
                environment: env
            })
        });

        const result = await response.json();

        if (!result.success) {
            alert('Error: ' + result.error);
            document.getElementById('ingest-btn').disabled = false;
            document.getElementById('stop-btn').style.display = 'none';
            updateStatus('idle', 'Ready');
            return;
        }

        currentExecutionId = result.execution_id;
        socket.emit('join_execution', { execution_id: currentExecutionId });
        addOutputLine('=== Ingest Started ===\n');

    } catch (error) {
        console.error('Error starting ingest:', error);
        alert('Error starting ingest: ' + error.message);
        document.getElementById('ingest-btn').disabled = false;
        document.getElementById('stop-btn').style.display = 'none';
        updateStatus('idle', 'Ready');
    }
}

async function stopExecution() {
    if (!currentExecutionId) return;
    try {
        await fetch(`/api/stop/${currentExecutionId}`, { method: 'POST' });
        addOutputLine('>>> Execution stopped\n');
    } catch (error) {
        console.error('Error stopping execution:', error);
    }
}

function onExecutionComplete(status = 'completed') {
    document.getElementById('ingest-btn').disabled = false;
    document.getElementById('stop-btn').style.display = 'none';

    if (status === 'error') {
        updateStatus('error', '⚠️ Error - Check output');
        addOutputLine('\n❌ === Ingest Failed ===');
    } else {
        updateStatus('completed', '✓ Completed');
        addOutputLine('\n✓ === Ingest Complete ===');
    }

    currentExecutionId = null;
}

function addOutputLine(text) {
    const outputDiv = document.getElementById('output');
    const line = document.createElement('div');
    line.className = 'output-line';
    line.textContent = text;
    outputDiv.appendChild(line);
    outputDiv.scrollTop = outputDiv.scrollHeight;
}

function clearOutput() {
    document.getElementById('output').innerHTML = '';
}

function updateStatus(status, text) {
    const indicator = document.getElementById('status');
    indicator.className = `status ${status}`;
    indicator.textContent = text;
}

// File Browser

async function openFileBrowser() {
    const directoryPath = document.getElementById('directory-path').value.trim();
    selectedBrowserFiles.clear();
    document.getElementById('file-browser').style.display = 'block';
    await loadDirectory(directoryPath || null);
}

function closeFileBrowser() {
    document.getElementById('file-browser').style.display = 'none';
}

async function loadDirectory(path = null) {
    const browserItems = document.getElementById('browser-items');
    browserItems.innerHTML = '<div class="browser-loading">Loading...</div>';

    try {
        const response = await fetch('/api/browse-directory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: path })
        });

        const result = await response.json();

        if (!result.success) {
            alert('Error: ' + result.error);
            return;
        }

        currentBrowserPath = result.current_path;
        document.getElementById('browser-current-path').textContent = currentBrowserPath;
        document.getElementById('directory-path').value = currentBrowserPath;

        renderBrowserItems(result.items);

    } catch (error) {
        console.error('Error loading directory:', error);
        browserItems.innerHTML = '<div class="browser-loading">Error loading directory</div>';
    }
}

function renderBrowserItems(items) {
    const browserItems = document.getElementById('browser-items');
    browserItems.innerHTML = '';

    const directories = items.filter(item => item.is_directory);
    const files = items.filter(item => !item.is_directory);

    directories.sort((a, b) => a.name.localeCompare(b.name));
    files.sort((a, b) => a.name.localeCompare(b.name));

    directories.forEach(item => {
        browserItems.appendChild(createBrowserItem(item, true));
    });

    files.forEach(item => {
        browserItems.appendChild(createBrowserItem(item, false));
    });

    if (items.length === 0) {
        browserItems.innerHTML = '<div class="browser-loading">Empty directory</div>';
    }
}

function createBrowserItem(item, isDirectory) {
    const div = document.createElement('div');
    div.className = 'browser-item';
    if (isDirectory) {
        div.classList.add('directory');
    }

    const icon = document.createElement('span');
    icon.className = 'icon';
    icon.textContent = isDirectory ? '📁' : '📄';

    const name = document.createElement('span');
    name.className = 'name';
    name.textContent = item.name;

    const size = document.createElement('span');
    size.className = 'size';
    if (!isDirectory && item.size !== null) {
        size.textContent = formatFileSize(item.size);
    }

    div.appendChild(icon);
    div.appendChild(name);
    div.appendChild(size);

    div.addEventListener('click', () => {
        if (isDirectory) {
            loadDirectory(item.path);
        } else {
            toggleFileSelection(item.path, div);
        }
    });

    if (selectedBrowserFiles.has(item.path)) {
        div.classList.add('selected');
    }

    return div;
}

function toggleFileSelection(filePath, element) {
    if (selectedBrowserFiles.has(filePath)) {
        selectedBrowserFiles.delete(filePath);
        element.classList.remove('selected');
    } else {
        selectedBrowserFiles.add(filePath);
        element.classList.add('selected');
    }
}

function selectBrowserFiles() {
    if (selectedBrowserFiles.size === 0) {
        alert('Please select at least one file');
        return;
    }

    selectedFiles = Array.from(selectedBrowserFiles);
    updateFileList();
    closeFileBrowser();
}

async function browserGoBack() {
    if (!currentBrowserPath) return;
    const parentPath = currentBrowserPath.split(/[\/\\]/).slice(0, -1).join('/') || '/';
    await loadDirectory(parentPath);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
