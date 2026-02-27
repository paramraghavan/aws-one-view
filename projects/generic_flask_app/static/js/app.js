let socket = null;
let currentExecutionId = null;
let selectedFiles = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeSocket();
    loadEnvironments();
    setupEventListeners();
});

function initializeSocket() {
    socket = io();

    socket.on('connect', () => {
        console.log('Connected to server');
    });

    socket.on('output', (data) => {
        console.log('[JS DEBUG] Received output:', data);
        addOutputLine(data.data);
    });

    socket.on('complete', (data) => {
        console.log('[JS DEBUG] Received complete:', data);
        onExecutionComplete(data.status);
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
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

        // Load saved default
        const saved = localStorage.getItem('default_env');
        if (saved && environments.includes(saved)) {
            select.value = saved;
            checkCachedPassword();
        }
    } catch (error) {
        console.error('Error loading environments:', error);
        addOutputLine('Error loading environments');
    }
}

function setupEventListeners() {
    // Environment change
    document.getElementById('environment').addEventListener('change', () => {
        // Clear password when environment changes
        document.getElementById('password').value = '';
        document.getElementById('cached-msg').style.display = 'none';
        checkCachedPassword();
    });

    // Set default environment
    document.getElementById('set-default').addEventListener('change', (e) => {
        if (e.target.checked) {
            const env = document.getElementById('environment').value;
            if (env) {
                localStorage.setItem('default_env', env);
            }
        } else {
            localStorage.removeItem('default_env');
        }
    });

    // File selection
    document.getElementById('files').addEventListener('change', (e) => {
        selectedFiles = Array.from(e.target.files).map(f => f.name);
        updateFileList();
    });

    // Buttons
    document.getElementById('ingest-btn').addEventListener('click', startIngest);
    document.getElementById('stop-btn').addEventListener('click', stopExecution);
    document.getElementById('clear-btn').addEventListener('click', clearOutput);
}

function checkCachedPassword() {
    const env = document.getElementById('environment').value;
    if (env) {
        fetch(`/api/get-password/${env}`)
            .then(r => r.json())
            .then(data => {
                if (data.has_password) {
                    document.getElementById('password').value = '(cached)';
                    document.getElementById('cached-msg').style.display = 'block';
                    document.getElementById('password').disabled = true;
                }
            });
    }
}

function updateFileList() {
    const container = document.getElementById('file-list');
    container.innerHTML = '';

    if (selectedFiles.length === 0) {
        container.innerHTML = '<p style="color: #999;">No files selected</p>';
        return;
    }

    selectedFiles.forEach(file => {
        const div = document.createElement('div');
        div.className = 'file-item';
        div.textContent = '📄 ' + file;
        container.appendChild(div);
    });
}

async function startIngest() {
    const env = document.getElementById('environment').value;
    let password = document.getElementById('password').value;
    const fileInput = document.getElementById('files');

    if (!env) {
        alert('Please select an environment');
        return;
    }

    if (!password || password === '(cached)') {
        alert('Please enter a password');
        return;
    }

    if (fileInput.files.length === 0) {
        alert('Please select files');
        return;
    }

    // Prepare files with full path (browser limitation: we get file names from input)
    const files = Array.from(fileInput.files).map(f => f.name);

    try {
        console.log('[JS DEBUG] startIngest called');
        console.log('[JS DEBUG] Environment:', env);
        console.log('[JS DEBUG] Files:', files);

        document.getElementById('ingest-btn').disabled = true;
        document.getElementById('stop-btn').style.display = 'inline-block';
        updateStatus('running', 'Running...');
        clearOutput();

        console.log('[JS DEBUG] Sending /api/ingest request');

        const response = await fetch('/api/ingest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                password: password,
                files: files,
                environment: env
            })
        });

        console.log('[JS DEBUG] /api/ingest response status:', response.status);

        const result = await response.json();

        console.log('[JS DEBUG] /api/ingest result:', result);

        if (!result.success) {
            alert('Error: ' + result.error);
            document.getElementById('ingest-btn').disabled = false;
            document.getElementById('stop-btn').style.display = 'none';
            updateStatus('idle', 'Ready');
            return;
        }

        currentExecutionId = result.execution_id;

        console.log('[JS DEBUG] Got execution_id:', currentExecutionId);
        console.log('[JS DEBUG] Joining SocketIO room...');

        // Join SocketIO room
        socket.emit('join_execution', { execution_id: currentExecutionId });

        addOutputLine('=== Ingest Started ===\n');

    } catch (error) {
        console.error('[JS DEBUG] Error starting ingest:', error);
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

    // Auto-scroll to bottom
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
