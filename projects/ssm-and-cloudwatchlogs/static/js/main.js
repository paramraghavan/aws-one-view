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

    const instanceLogStates = {};

    function loadInstanceLogs(instanceId, commandId) {
        if (instanceLogStates[instanceId]) return;

        instanceLogStates[instanceId] = true;
        fetch(`/logs/${commandId}/${instanceId}`)
            .then(response => response.json())
            .then(data => {
                document.getElementById(`outputLogs${instanceId}`).textContent =
                    data.output || 'No output logs available';
                document.getElementById(`errorLogs${instanceId}`).textContent =
                    data.error || 'No error logs available';
            })
            .catch(error => {
                console.error('Error fetching logs:', error);
                document.getElementById(`outputLogs${instanceId}`).textContent =
                    'Error loading logs';
                document.getElementById(`errorLogs${instanceId}`).textContent =
                    'Error loading logs';
            });
    }

    document.querySelectorAll('.accordion-button').forEach(button => {
        button.addEventListener('click', function() {
            const instanceId = this.textContent.trim().split(' ')[1];
            const commandId = '{{ command.CommandId }}';
            loadInstanceLogs(instanceId, commandId);
        });
    });