    async function copyContent(elementId) {
        const content = document.getElementById(elementId).textContent;
        try {
            await navigator.clipboard.writeText(content);
            const btn = event.target;
            btn.textContent = 'Copied!';
            setTimeout(() => btn.textContent = 'Copy', 2000);
        } catch (err) {
            console.error('Failed to copy: ', err);
        }
    }