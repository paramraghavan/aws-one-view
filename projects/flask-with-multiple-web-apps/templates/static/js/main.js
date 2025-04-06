// Common JavaScript for all apps
document.addEventListener('DOMContentLoaded', function() {
    console.log('Multi-App Flask Demo loaded');

    // Add current year to footer copyright
    const footerYear = document.querySelector('footer p');
    if (footerYear) {
        const currentYear = new Date().getFullYear();
        footerYear.textContent = footerYear.textContent.replace('2025', currentYear);
    }
});