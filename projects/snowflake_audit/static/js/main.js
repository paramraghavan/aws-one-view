// Main JavaScript for Snowflake Operations Monitor

$(document).ready(function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);

    // Toggle expand all/collapse all for accordion
    $('#expandAll').click(function() {
        $('.accordion-collapse').collapse('show');
    });

    $('#collapseAll').click(function() {
        $('.accordion-collapse').collapse('hide');
    });

    // Make cards with tables full width on small screens
    function adjustCardWidths() {
        if (window.innerWidth < 768) {
            $('.card').addClass('w-100');
        } else {
            $('.card').removeClass('w-100');
        }
    }

    // Initial call and event binding
    adjustCardWidths();
    $(window).resize(adjustCardWidths);

    // Format pre code blocks
    $('pre code').each(function() {
        const content = $(this).html();
        const formattedContent = formatSql(content);
        $(this).html(formattedContent);
    });

    // Simple SQL formatter
    function formatSql(sql) {
        if (!sql) return '';

        // Keywords to capitalize
        const keywords = [
            'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE',
            'CREATE', 'DROP', 'ALTER', 'TABLE', 'JOIN', 'LEFT', 'RIGHT',
            'INNER', 'OUTER', 'ON', 'AND', 'OR', 'IN', 'NOT', 'NULL',
            'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'OFFSET', 'UNION',
            'ALL', 'DISTINCT', 'AS', 'BETWEEN', 'LIKE', 'IS'
        ];

        let formattedSql = sql;

        // Capitalize keywords
        keywords.forEach(keyword => {
            const regex = new RegExp('\\b' + keyword + '\\b', 'gi');
            formattedSql = formattedSql.replace(regex, keyword);
        });

        // Add line breaks for better readability
        formattedSql = formattedSql
            .replace(/\s+FROM\s+/g, '\nFROM ')
            .replace(/\s+WHERE\s+/g, '\nWHERE ')
            .replace(/\s+ORDER BY\s+/g, '\nORDER BY ')
            .replace(/\s+GROUP BY\s+/g, '\nGROUP BY ')
            .replace(/\s+HAVING\s+/g, '\nHAVING ')
            .replace(/\s+LIMIT\s+/g, '\nLIMIT ')
            .replace(/\s+UNION\s+/g, '\nUNION\n')
            .replace(/\s+JOIN\s+/g, '\nJOIN ')
            .replace(/\s+AND\s+/g, '\n  AND ')
            .replace(/\s+OR\s+/g, '\n  OR ');

        return formattedSql;
    }

    // Form validation for interval inputs
    $('input[type="number"]').on('input', function() {
        const min = parseInt($(this).attr('min')) || 1;
        const max = parseInt($(this).attr('max')) || 168;

        let value = parseInt($(this).val());

        if (isNaN(value) || value < min) {
            value = min;
        } else if (value > max) {
            value = max;
        }

        $(this).val(value);
    });

    // Enable database search functionality
    $('#databaseSearch').on('keyup', function() {
        const searchTerm = $(this).val().toLowerCase();

        $('.accordion-item').each(function() {
            const databaseName = $(this).find('.accordion-button strong').text().toLowerCase();

            if (databaseName.includes(searchTerm)) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    });

    // Copy query to clipboard
    $('.copy-query').click(function() {
        const queryText = $(this).closest('.modal').find('pre code').text();

        navigator.clipboard.writeText(queryText).then(function() {
            // Show copied message
            const originalHtml = $(this).html();
            $(this).html('<i class="fas fa-check"></i> Copied!');

            setTimeout(function() {
                $(this).html(originalHtml);
            }.bind(this), 2000);
        }.bind(this));
    });
});