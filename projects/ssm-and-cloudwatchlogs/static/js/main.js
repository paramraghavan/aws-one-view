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


// Set default dates in EST
const now = new Date();
const yesterday = new Date(now);
yesterday.setHours(now.getHours() - 24);

// Convert to EST
const estOffset = -5; // EST offset from UTC
const utcOffset = now.getTimezoneOffset() / 60;
const offsetDiff = estOffset - (-utcOffset);

now.setHours(now.getHours() + offsetDiff);
yesterday.setHours(yesterday.getHours() + offsetDiff);

// Format dates for datetime-local input
document.getElementById('start_date').value = yesterday.toISOString().slice(0, 16);
document.getElementById('end_date').value = now.toISOString().slice(0, 16);
