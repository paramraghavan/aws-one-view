async function viewLogs(commandId) {
    try {
        const response = await fetch(`/logs/${commandId}`);
        const data = await response.json();

        document.getElementById('outputLogs').textContent = data.output || 'No output logs available';
        document.getElementById('errorLogs').textContent = data.error || 'No error logs available';
    } catch (error) {
        console.error('Error fetching logs:', error);
        alert('Error fetching logs. Please try again.');
    }
}